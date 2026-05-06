from pathlib import Path
import numpy as np
from napari.viewer import Viewer
from napari.layers import Layer
from .registry import REGISTRY
from .recorder import PipelineRecorder
from .functions import convert_to_8bit, _is_binary
from qtpy.QtWidgets import QApplication
from tqdm import tqdm

from .constants import (
    BASE_LAYER_PLACEHOLDER,
    SOURCE_DIR_PLACEHOLDER,
    LAYER_NAME_PLACEHOLDER,
)


def _substitute(name: str | None, base_layer: str) -> str | None:
    """Replace $base placeholder with actual layer name."""
    if name is None:
        return None
    return name.replace(BASE_LAYER_PLACEHOLDER, base_layer)


def _resolve_savepath(template: str, layer: Layer) -> Path:
    meta = layer.metadata if hasattr(layer, "metadata") else {}
    source_dir = str(meta.get("source_dir", Path.home()))
    layer_name = layer.name if hasattr(layer, "name") else "unknown_layer"
    resolved = template.replace(SOURCE_DIR_PLACEHOLDER, source_dir).replace(
        LAYER_NAME_PLACEHOLDER, layer_name
    )
    return Path(resolved)


def replay_pipeline(
    recorder: PipelineRecorder,
    viewer: Viewer,
    base_layer_name: str | None = None,
) -> None:
    if base_layer_name is None:
        return

    base_layer_object = viewer.layers[base_layer_name]

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
                if layer.data.dtype == np.float32:
                    layer.data = convert_to_8bit(layer.data)
                inputs[arg_name] = layer.data

        # if path is given, the func will not return data for a new layer
        # but use that path to save something (Hmap/BVmap/metrics)
        # and the return value will be None
        if "path" in step["params"]:
            resolved_path = _resolve_savepath(step["params"]["path"], base_layer_object)
            result = func(**inputs, **{**step["params"], "path": resolved_path})
        else:
            result = func(**inputs, **step["params"])

        output_name = step["output_layer"]

        if result is None and output_name is None:
            QApplication.processEvents()
            continue

        if base_layer_name is not None:
            output_name = _substitute(output_name, base_layer_name)

        affine = (
            base_layer_object.affine.affine_matrix
            if hasattr(base_layer_object, "affine")
            else np.eye(4)
        )
        metadata = (
            {**base_layer_object.metadata}
            if hasattr(base_layer_object, "metadata")
            else {}
        )
        scale = (
            base_layer_object.scale
            if hasattr(base_layer_object, "scale")
            else (1.0, 1.0, 1.0)
        )
        axis_labels = (
            base_layer_object.axis_labels
            if hasattr(base_layer_object, "axis_labels")
            else None
        )
        units = base_layer_object.units if hasattr(base_layer_object, "units") else None

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

        QApplication.processEvents()


def replay_on_batch(
    recorder: PipelineRecorder, viewer: Viewer, source_folder: Path
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
