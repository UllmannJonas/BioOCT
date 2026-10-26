import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from qtpy.QtWidgets import QApplication
from tqdm import tqdm

from .output_paths import resolve_output_path
from .recorder import PipelineRecorder
from .registry import REGISTRY, FunctionSpec

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer


class _LayerProperties(TypedDict):
    affine: Any
    metadata: dict[str, Any]
    scale: Any
    axis_labels: Any
    units: Any


class _ResolvedStep(TypedDict):
    spec: FunctionSpec
    kwargs: dict[str, Any]
    params: dict[str, Any]
    output_name: str | None
    primary_input_name: str | None


class PipelineReplayError(RuntimeError):
    def __init__(
        self,
        step_index: int,
        function_name: str,
        cause: BaseException | None = None,
    ) -> None:
        self.step_index = step_index
        self.function_name = function_name
        message = f"Pipeline replay failed at step {step_index} ({function_name})"
        if cause is not None:
            message += f": {type(cause).__name__}: {cause}"
        super().__init__(message)


class PipelineDryRunError(ValueError):
    pass


_SUPPORTED_REPLAY_CONTEXTS = {"layername", "roi_corner_points"}


def dry_run_pipeline(recorder: PipelineRecorder) -> None:
    issues: list[str] = []

    for step_nr, step in enumerate(recorder.steps, start=1):
        step_index = step.get("step", step_nr)
        function_name = step.get("function", "<unknown>")
        spec = REGISTRY.get(function_name)
        if spec is None:
            issues.append(
                f"Step {step_index} ({function_name}): function is not registered"
            )
            continue

        unsupported_context = [
            context_name
            for context_name in spec.context
            if context_name not in _SUPPORTED_REPLAY_CONTEXTS
        ]
        if unsupported_context:
            issues.append(
                f"Step {step_index} ({function_name}): unsupported replay context "
                f"{', '.join(repr(name) for name in unsupported_context)}"
            )

        params = step["params"]
        if "path" in params and "output_filename" in params:
            issues.append(
                f"Step {step_index} ({function_name}): a pipeline step cannot "
                "contain both 'path' and 'output_filename' parameters"
            )

    if issues:
        raise PipelineDryRunError("Pipeline dry-run failed:\n- " + "\n- ".join(issues))


def _substitute(name: str | None, base_layer: str) -> str | None:
    """Replace $base placeholder with actual layer name."""
    base = "$base"

    if name is None:
        return name
    if name == base or name.startswith(f"{base}_"):
        return f"{base_layer}{name[len(base) :]}"
    return name


def _layer_properties(layer: "napari.layers.Layer") -> _LayerProperties:
    return {
        "affine": layer.affine.affine_matrix if hasattr(layer, "affine") else None,
        "metadata": dict(layer.metadata) if hasattr(layer, "metadata") else {},
        "scale": layer.scale if hasattr(layer, "scale") else None,
        "axis_labels": layer.axis_labels if hasattr(layer, "axis_labels") else None,
        "units": layer.units if hasattr(layer, "units") else None,
    }


def validate_output_folder(output_folder: Path | None) -> None:
    if output_folder is None:
        return
    if not output_folder.exists() or not output_folder.is_dir():
        raise ValueError(f"Output folder does not exist: {output_folder}")

    try:
        with tempfile.NamedTemporaryFile(
            prefix=".bio_oct_write_test_", dir=output_folder
        ):
            pass
    except OSError as exc:
        raise ValueError(f"Output folder is not writable: {output_folder}") from exc


def _source_directory(
    layer: "napari.layers.Layer",
    base_layer: "napari.layers.Layer",
) -> Path:
    layer_metadata = layer.metadata if hasattr(layer, "metadata") else {}
    base_metadata = base_layer.metadata if hasattr(base_layer, "metadata") else {}
    source_dir = layer_metadata.get(
        "source_dir", base_metadata.get("source_dir", Path.home())
    )
    return Path(source_dir)


def _resolve_savepath(
    path: str,
    base_layer: "napari.layers.Layer",
    output_folder: Path | None,
) -> Path:
    source_dir_placeholder = "$source_dir"
    layer_name_placeholder = "$layer_name"

    source_dir = str(
        output_folder
        if output_folder is not None
        else _source_directory(base_layer, base_layer)
    )
    layer_name = base_layer.name if hasattr(base_layer, "name") else "unknown_layer"
    resolved = path.replace(source_dir_placeholder, source_dir).replace(
        layer_name_placeholder, layer_name
    )
    return Path(resolved)


def _resolve_output_filename(
    filename: str,
    primary_input_layer: "napari.layers.Layer | None",
    base_layer: "napari.layers.Layer",
    output_folder: Path | None,
) -> Path:
    input_layer = primary_input_layer if primary_input_layer is not None else base_layer
    destination = (
        output_folder
        if output_folder is not None
        else _source_directory(input_layer, base_layer)
    )
    return resolve_output_path(filename, input_layer, destination)


def _resolve_step(
    step: dict[str, Any],
    viewer: "napari.viewer.Viewer",
    base_layer_name: str,
    output_folder: Path | None = None,
) -> _ResolvedStep:
    function_name = str(step.get("function", "<unknown>"))
    spec = REGISTRY[function_name]
    input_layer_names = {
        arg_name: _substitute(layer_name, base_layer_name)
        for arg_name, layer_name in step["input_layers"].items()
    }
    primary_input_name = next(iter(input_layer_names.values()), None)
    output_name = _substitute(step["output_layer"], base_layer_name)

    inputs: dict[str, Any] = {}
    primary_input_layer = None
    for index, (arg_name, layer_name) in enumerate(input_layer_names.items()):
        if layer_name is None:
            inputs[arg_name] = None
        else:
            layer = viewer.layers[layer_name]
            inputs[arg_name] = layer.data
            if index == 0:
                primary_input_layer = layer

    params: dict[str, Any] = step["params"]
    context: dict[str, Any] = {}
    for context_name in spec.context:
        if context_name == "layername":
            context[context_name] = base_layer_name
        elif context_name == "roi_corner_points":
            if context_name not in params and primary_input_layer is not None:
                roi_points = primary_input_layer.metadata.get("roi_corner_points")
                if roi_points is None:
                    roi_points = primary_input_layer.metadata.get("roi_points")
                if roi_points is not None:
                    context[context_name] = roi_points
        else:
            raise ValueError(f"Unsupported replay context: {context_name}")

    if "path" in params and "output_filename" in params:
        raise ValueError(
            "A pipeline step cannot contain both 'path' and "
            "'output_filename' parameters"
        )
    kwargs = {**inputs, **context, **params}
    if "output_filename" in kwargs:
        output_filename = kwargs.pop("output_filename")
        if not isinstance(output_filename, str):
            raise ValueError("'output_filename' must be a string filename template")
        base_layer = viewer.layers[base_layer_name]
        kwargs["path"] = _resolve_output_filename(
            output_filename,
            primary_input_layer,
            base_layer,
            output_folder,
        )
    elif "path" in kwargs:
        path_template = kwargs["path"]
        if not isinstance(path_template, str):
            raise ValueError("Legacy 'path' parameter must be a string")
        base_layer = viewer.layers[base_layer_name]
        kwargs["path"] = _resolve_savepath(path_template, base_layer, output_folder)

    return {
        "spec": spec,
        "kwargs": kwargs,
        "params": params,
        "output_name": output_name,
        "primary_input_name": primary_input_name,
    }


def _execute_step(resolved: _ResolvedStep) -> Any:
    return resolved["spec"].func(**resolved["kwargs"])


def _apply_result(
    result: Any,
    resolved: _ResolvedStep,
    viewer: "napari.viewer.Viewer",
) -> None:
    spec = resolved["spec"]
    if spec.output is None:
        QApplication.processEvents()
        return
    if result is None:
        raise ValueError("Function returned no data for an output layer")

    output_name = resolved["output_name"]
    if output_name in [layer.name for layer in viewer.layers]:
        output_layer = viewer.layers[output_name]
        output_layer.data = result
        if spec.after is not None:
            spec.after(output_layer, resolved["params"])
        output_layer.refresh()
    else:
        if resolved["primary_input_name"] is None:
            raise ValueError(
                "Cannot create an output layer for a step without a primary input layer"
            )
        primary_layer = viewer.layers[resolved["primary_input_name"]]
        layer_properties = _layer_properties(primary_layer)

        if spec.output == "labels":
            output_layer = viewer.add_labels(  # type: ignore[attr-defined]
                result, name=output_name, **layer_properties
            )
        else:
            output_layer = viewer.add_image(
                result,
                name=output_name,
                **layer_properties,
                contrast_limits=(0, 255),
            )
        if spec.after is not None:
            spec.after(output_layer, resolved["params"])

    QApplication.processEvents()


def replay_pipeline(
    recorder: PipelineRecorder,
    viewer: "napari.viewer.Viewer",
    base_layer_name: str | None = None,
    output_folder: Path | None = None,
) -> None:
    if base_layer_name is None:
        return
    validate_output_folder(output_folder)
    dry_run_pipeline(recorder)

    _run_pipeline_steps(recorder, viewer, base_layer_name, output_folder)


def _run_pipeline_steps(
    recorder: PipelineRecorder,
    viewer: "napari.viewer.Viewer",
    base_layer_name: str,
    output_folder: Path | None,
) -> None:
    for step_position, step in enumerate(recorder.steps, start=1):
        function_name = str(step.get("function", "<unknown>"))
        step_index = step.get("step", step_position)
        try:
            resolved = _resolve_step(step, viewer, base_layer_name, output_folder)
            result = _execute_step(resolved)
            _apply_result(result, resolved, viewer)
        except Exception as exc:
            raise PipelineReplayError(step_index, function_name, exc) from exc


def replay_on_batch(
    recorder: PipelineRecorder,
    viewer: "napari.viewer.Viewer",
    source_folder: Path,
    output_folder: Path | None = None,
    on_progress: Callable[[int, int, Path | None], None] | None = None,
) -> None:
    validate_output_folder(output_folder)
    dry_run_pipeline(recorder)
    print()
    print("#" * 20)
    print("Batch Pipeline Replay started...")

    files = sorted(source_folder.glob("*.oct"))
    if on_progress is not None:
        on_progress(0, len(files), None)

    if not files:
        print("No .oct files found in folder.")
        return

    errors: list[dict] = []

    for file_index, f in enumerate(
        tqdm(files, desc="Processing files", unit="file"), 1
    ):
        if on_progress is not None:
            on_progress(file_index - 1, len(files), f)

        print(f"\nProcessing: {f.stem}")

        try:
            viewer.open(f, plugin="bio_oct")
            QApplication.processEvents()
            _run_pipeline_steps(
                recorder=recorder,
                viewer=viewer,
                base_layer_name=f.stem,
                output_folder=output_folder,
            )
        except Exception as e:  # noqa: BLE001 - batch must continue on any per-file error
            errors.append({"file": f, "error": e})
            print("=" * 10)
            print(f"Error on file: {f}")
            print(e)
            print("Continuing with next file...")
        finally:
            viewer.layers.clear()
            if on_progress is not None:
                on_progress(file_index, len(files), f)
            QApplication.processEvents()

    print()
    print("=" * 20)
    print("Batch finished!")
    print(f"Total Errors: {len(errors)}")
    if errors:
        print("Files with errors:")
        for err in errors:
            print(f">> {err['file']}")
    print("=" * 20)
