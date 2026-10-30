from typing import TYPE_CHECKING

import numpy as np

# Third party imports
from magicgui import magic_factory
from numpy import asarray

# Local imports
from ..functions import functions as fn
from ..shared_utility import resolve_output_path
from ._widget_helpers import _run_and_record_action

if TYPE_CHECKING:
    import napari.layers


@magic_factory(
    call_button="Create Height Map",
    segmentation={"label": "Segmentation"},
    substratum={"label": "Substratum"},
    colorbar={"label": "Add Colorbar"},
    scalebar={"label": "Add Scalebar"},
    axes={"label": "Show Axes"},
    max_height_um={
        "label": "Max Height [µm]",
        "max": 10000,
        "tooltip": "Maximum height (µm) used for scaling the height map.",
    },
    preview={
        "label": "Preview",
        "tooltip": "When checked, only preview plot is shown instead of saving to file.",
    },
)
def create_height_map_widget(
    segmentation: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
    max_height_um: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
    preview: bool = True,
) -> None:
    spacing = segmentation.metadata.get("spacing", None)
    output_filename = "{input_layer}_Hmap.tiff"
    inputs = {
        "segmentation": asarray(segmentation.data),
        "preview": preview,
    }
    input_layers: dict[str, str | None] = {"segmentation": segmentation.name}
    if substratum is not None:
        inputs["substratum"] = asarray(substratum.data)
        input_layers["substratum"] = substratum.name

    if preview:
        fn.create_height_map(
            **inputs,
            spacing=asarray(spacing) if spacing is not None else None,
            max_height_um=max_height_um,
            colorbar=colorbar,
            scalebar=scalebar,
            axes=axes,
            path=resolve_output_path(output_filename, segmentation),
        )
        return

    _run_and_record_action(
        func=fn.create_height_map,
        inputs=inputs,
        input_layers=input_layers,
        output_layer=None,
        params={
            "spacing": spacing,
            "max_height_um": max_height_um,
            "colorbar": colorbar,
            "scalebar": scalebar,
            "axes": axes,
            "output_filename": output_filename,
        },
        resolve_path=lambda name: resolve_output_path(name, segmentation),
    )


@magic_factory(
    call_button="Create Biovolume Map",
    segmentation={"label": "Segmentation"},
    substratum={"label": "Substratum"},
    colorbar={"label": "Add Colorbar"},
    scalebar={"label": "Add Scalebar"},
    axes={"label": "Show Axes"},
    max_height_um={
        "label": "Max Height [µm]",
        "max": 10000,
        "tooltip": "Maximum height (µm) used for scaling the height map.",
    },
    preview={
        "label": "Preview",
        "tooltip": "When checked, only preview plot is shown instead of saving to file.",
    },
)
def create_bv_map_widget(
    segmentation: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
    max_height_um: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
    preview: bool = True,
) -> None:
    spacing = segmentation.metadata.get("spacing", None)
    output_filename = "{input_layer}_BVmap.tiff"
    inputs = {
        "segmentation": asarray(segmentation.data),
        "preview": preview,
    }
    input_layers: dict[str, str | None] = {"segmentation": segmentation.name}
    if substratum is not None:
        inputs["substratum"] = asarray(substratum.data)
        input_layers["substratum"] = substratum.name

    if preview:
        fn.create_bv_map(
            **inputs,
            spacing=asarray(spacing) if spacing is not None else None,
            max_height_um=max_height_um,
            colorbar=colorbar,
            scalebar=scalebar,
            axes=axes,
            path=resolve_output_path(output_filename, segmentation),
        )
        return

    _run_and_record_action(
        func=fn.create_bv_map,
        inputs=inputs,
        input_layers=input_layers,
        output_layer=None,
        params={
            "spacing": spacing,
            "max_height_um": max_height_um,
            "colorbar": colorbar,
            "scalebar": scalebar,
            "axes": axes,
            "output_filename": output_filename,
        },
        resolve_path=lambda name: resolve_output_path(name, segmentation),
    )


@magic_factory(
    call_button="Save Metrics to CSV",
    segmentation={"label": "Segmentation"},
    substratum={"label": "Substratum"},
)
def calculate_metrics_widget(
    segmentation: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
) -> None:
    spacing = segmentation.metadata.get("spacing")
    assert spacing is not None

    roi_corner_points = segmentation.metadata.get("roi_corner_points", None)
    if roi_corner_points is not None:
        roi_corner_points = np.asarray(roi_corner_points, dtype=np.int32).tolist()

    inputs = {
        "segmentation": asarray(segmentation.data),
        "layername": segmentation.name,
    }
    input_layers: dict[str, str | None] = {"segmentation": segmentation.name}
    if substratum is not None:
        inputs["substratum"] = asarray(substratum.data)
        input_layers["substratum"] = substratum.name

    params = {
        "spacing": spacing,
        "output_filename": "batch_metrics.csv",
    }
    if roi_corner_points is not None:
        params["roi_corner_points"] = roi_corner_points

    _run_and_record_action(
        func=fn.calculate_metrics,
        inputs=inputs,
        input_layers=input_layers,
        output_layer=None,
        params=params,
        resolve_path=lambda name: resolve_output_path(name, segmentation),
    )
