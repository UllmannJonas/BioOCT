from pathlib import Path
import inspect
from typing import TYPE_CHECKING, Any, TypedDict

from .registry import REGISTRY
from .recorder import PipelineRecorder
from .functions import _is_binary
from qtpy.QtWidgets import QApplication
from tqdm import tqdm

from .constants import (
    BASE_LAYER_PLACEHOLDER,
    SOURCE_DIR_PLACEHOLDER,
    LAYER_NAME_PLACEHOLDER,
)

if TYPE_CHECKING:
    import napari.viewer
    import napari.layers


class _LayerProperties(TypedDict):
    affine: Any
    metadata: dict[str, Any]
    scale: Any
    axis_labels: Any
    units: Any


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


def _substitute(name: str | None, base_layer: str) -> str | None:
    """Replace $base placeholder with actual layer name."""
    if name is None:
        return None
    return name.replace(BASE_LAYER_PLACEHOLDER, base_layer)


def _layer_properties(layer: "napari.layers.Layer") -> _LayerProperties:
    return {
        "affine": layer.affine.affine_matrix if hasattr(layer, "affine") else None,
        "metadata": dict(layer.metadata) if hasattr(layer, "metadata") else {},
        "scale": layer.scale if hasattr(layer, "scale") else None,
        "axis_labels": layer.axis_labels if hasattr(layer, "axis_labels") else None,
        "units": layer.units if hasattr(layer, "units") else None,
    }


def _resolve_savepath(template: str, layer: "napari.layers.Layer") -> Path:
    meta = layer.metadata if hasattr(layer, "metadata") else {}
    source_dir = str(meta.get("source_dir", Path.home()))
    layer_name = layer.name if hasattr(layer, "name") else "unknown_layer"
    resolved = template.replace(SOURCE_DIR_PLACEHOLDER, source_dir).replace(
        LAYER_NAME_PLACEHOLDER, layer_name
    )
    return Path(resolved)


def replay_pipeline(
    recorder: PipelineRecorder,
    viewer: "napari.viewer.Viewer",
    base_layer_name: str | None = None,
) -> None:
    if base_layer_name is None:
        return

    for step_position, step in enumerate(recorder.steps, start=1):
        function_name = str(step.get("function", "<unknown>"))
        step_index = step.get("step", step_position)
        try:
            func = REGISTRY[function_name]
            input_layer_names = {
                arg_name: _substitute(layer_name, base_layer_name)
                for arg_name, layer_name in step["input_layers"].items()
            }
            primary_input_name = next(iter(input_layer_names.values()), None)
            output_name = _substitute(step["output_layer"], base_layer_name)

            inputs = {}
            for arg_name, layer_name in input_layer_names.items():
                if layer_name is None:
                    inputs[arg_name] = None
                else:
                    layer = viewer.layers[layer_name]
                    inputs[arg_name] = layer.data

            # if path is given, the func will not return data for a new layer
            # but use that path to save something (Hmap/BVmap/metrics)
            # and the return value will be None
            extra = {}
            if "layername" in inspect.signature(func).parameters:
                extra["layername"] = base_layer_name
            if "roi_corner_points" in inspect.signature(func).parameters:
                if "roi_corner_points" not in step["params"]:
                    if primary_input_name is not None:
                        layer = viewer.layers[primary_input_name]
                        roi_points = layer.metadata.get("roi_corner_points")
                        if roi_points is None:
                            roi_points = layer.metadata.get("roi_points")
                        if roi_points is not None:
                            extra["roi_corner_points"] = roi_points
            if "path" in step["params"]:
                resolved_path = _resolve_savepath(
                    step["params"]["path"], viewer.layers[base_layer_name]
                )
                result = func(
                    **inputs, **{**step["params"], "path": resolved_path}, **extra
                )
            else:
                result = func(**inputs, **step["params"], **extra)

            if result is None:
                if output_name is None:
                    # fn used for side-effect (e.g. saving a file), return=None -> skip layer creation
                    QApplication.processEvents()
                    continue
                raise ValueError("Function returned no data for an output layer")
            if output_name in [lay.name for lay in viewer.layers]:
                # layer already exists -> only update layer, skip creation
                viewer.layers[output_name].data = result
                viewer.layers[output_name].refresh()
                QApplication.processEvents()
                continue

            if primary_input_name is None:
                raise ValueError(
                    "Cannot create an output layer for a step without a primary input layer"
                )
            primary_layer = viewer.layers[primary_input_name]
            layer_properties = _layer_properties(primary_layer)

            if _is_binary(result):
                viewer.add_labels(result, name=output_name, **layer_properties)
            else:
                viewer.add_image(
                    result,
                    name=output_name,
                    **layer_properties,
                    contrast_limits=(0, 255),
                )

            if (
                function_name == "define_roi"
                and "roi_corner_points" in step["params"]
                and output_name is not None
            ):
                viewer.layers[output_name].metadata["roi_corner_points"] = step[
                    "params"
                ]["roi_corner_points"]

            QApplication.processEvents()
        except Exception as exc:
            raise PipelineReplayError(step_index, function_name, exc) from exc


def replay_on_batch(
    recorder: PipelineRecorder, viewer: "napari.viewer.Viewer", source_folder: Path
) -> None:
    print()
    print("#" * 20)
    print("Batch Pipeline Replay started...")

    files = sorted(source_folder.glob("*.oct"))
    if not files:
        print("No .oct files found in folder.")
        return

    errors: list[dict] = []

    for f in tqdm(files, desc="Processing files", unit="file"):
        print(f"\nProcessing: {f.stem}")

        try:
            viewer.open(f, plugin="bio_oct")
            QApplication.processEvents()
            replay_pipeline(recorder=recorder, viewer=viewer, base_layer_name=f.stem)
        except Exception as e:
            errors.append({"file": f, "error": e})
            print("=" * 10)
            print(f"Error on file: {f}")
            print(e)
            print("Continuing with next file...")
        finally:
            viewer.layers.clear()
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
