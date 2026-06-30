from pathlib import Path
import inspect
from typing import TYPE_CHECKING

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


def _substitute(name: str | None, base_layer: str) -> str | None:
    """Replace $base placeholder with actual layer name."""
    if name is None:
        return None
    return name.replace(BASE_LAYER_PLACEHOLDER, base_layer)


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

    for step in recorder.steps:
        func = REGISTRY[step["function"]]

        inputs = {}
        for arg_name, layer_name in step["input_layers"].items():
            # replace $base placeholder if base layer was given
            if base_layer_name is not None:
                layer_name = _substitute(layer_name, base_layer_name)

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
                # Only inject from metadata if not already in params
                input_layer_name = _substitute(
                    next(iter(step["input_layers"].values())), base_layer_name
                )
                if input_layer_name is not None:
                    try:
                        layer = viewer.layers[input_layer_name]
                        roi_points = layer.metadata.get("roi_corner_points")
                        if roi_points is None:
                            roi_points = layer.metadata.get("roi_points")
                        if roi_points is not None:
                            extra["roi_corner_points"] = roi_points
                    except KeyError:
                        pass
        if "path" in step["params"]:
            resolved_path = _resolve_savepath(
                step["params"]["path"], viewer.layers[base_layer_name]
            )
            result = func(
                **inputs, **{**step["params"], "path": resolved_path}, **extra
            )
        else:
            result = func(**inputs, **step["params"], **extra)

        output_name = step["output_layer"]
        if base_layer_name is not None:
            output_name = _substitute(output_name, base_layer_name)

        if result is None and output_name is None:
            # fn used for side-effect (e.g. saving a file), return=None -> skip layer creation
            QApplication.processEvents()
            continue
        elif output_name in [lay.name for lay in viewer.layers]:
            # layer already exists -> only update layer, skip creation
            viewer.layers[output_name].data = result
            viewer.layers[output_name].refresh()
            QApplication.processEvents()
            continue

        primary_input_name = _substitute(
            next(iter(step["input_layers"].values())), base_layer_name
        )
        assert primary_input_name is not None
        primary_layer = viewer.layers[primary_input_name]

        affine = (
            primary_layer.affine.affine_matrix
            if hasattr(primary_layer, "affine")
            else None
        )
        scale = primary_layer.scale if hasattr(primary_layer, "scale") else None
        axis_labels = (
            primary_layer.axis_labels if hasattr(primary_layer, "axis_labels") else None
        )
        units = primary_layer.units if hasattr(primary_layer, "units") else None
        metadata = (
            {**primary_layer.metadata} if hasattr(primary_layer, "metadata") else {}
        )

        if _is_binary(result):
            viewer.add_labels(
                result,
                name=output_name,
                affine=affine,
                metadata=metadata,
                scale=scale,
                axis_labels=axis_labels,
                units=units,
            )
        else:
            viewer.add_image(
                result,
                name=output_name,
                affine=affine,
                metadata=metadata,
                scale=scale,
                axis_labels=axis_labels,
                units=units,
                contrast_limits=(0, 255),
            )

        if (
            step["function"] == "define_roi"
            and "roi_corner_points" in step["params"]
            and output_name is not None
        ):
            viewer.layers[output_name].metadata["roi_corner_points"] = step["params"][
                "roi_corner_points"
            ]

        QApplication.processEvents()


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
            viewer.open(f, plugin="oct_analysis")
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
