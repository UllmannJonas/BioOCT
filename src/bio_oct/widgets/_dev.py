# region IMPORTS
# Python native imports
import json
from typing import TYPE_CHECKING, cast

import numpy as np

# Third party imports
from magicgui import magic_factory
from numpy import asarray

# Local imports
from ..functions import functions as fn
from ..shared_utility import copy_layer_properties
from ._widget_helpers import _get_napari_image_class

if TYPE_CHECKING:
    import napari.layers
    import napari.types


@magic_factory(
    call_button="Set Spacing",
    spacing_bscans={"label": "B-Scan Spacing [Y]", "widget_type": "LineEdit"},
    spacing_axial={"label": "Axial Spacing [Z]", "widget_type": "LineEdit"},
    spacing_lateral={"label": "Lateral Spacing [X]", "widget_type": "LineEdit"},
)
def set_spacing_widget(
    layer: "napari.layers.Layer",
    spacing_bscans: str,
    spacing_axial: str,
    spacing_lateral: str,
):
    layer.metadata["spacing"] = (
        float(spacing_bscans),
        float(spacing_axial),
        float(spacing_lateral),
    )
    if hasattr(layer, "affine") and layer.affine is not None:
        # Update affine matrix to reflect new spacing
        new_affine = np.copy(layer.affine.affine_matrix)
        np.fill_diagonal(new_affine, list(layer.metadata["spacing"]) + [1])
        layer.affine = new_affine
    layer.refresh()


@magic_factory(
    call_button="Print Metadata",
    result_widget=True,
)
def print_metadata(layer: "napari.layers.Layer"):
    info = {
        "metadata": layer.metadata,
        "name": layer.name,
        "affine": layer.affine.affine_matrix,
        "opacity": layer.opacity,
        "source": layer.source,
        "units": layer.units,
        "ndim": layer.ndim,
        "contrast_limits": layer.contrast_limits
        if isinstance(layer, _get_napari_image_class())
        else None,
        "layer_type": layer._type_string,
    }
    return json.dumps(info, indent=2, default=str)


@magic_factory(
    call_button="Expand Surface",
    expand={"label": "Expand by [px]", "min": 0, "max": 10, "widget_type": "Slider"},
)
def expand_coords(
    coords: "napari.layers.Labels", expand: int = 0
) -> "napari.types.LayerDataTuple":
    label = fn._get_color_id(asarray(coords.data))
    surface = np.argmax(asarray(coords.data), axis=1)
    z = np.arange(coords.data.shape[1])[None, :, None]

    mask = (z >= (surface[:, None, :] - expand)) & (z <= (surface[:, None, :] + expand))
    mask = mask.astype(np.uint8) * label

    layer_properties = {
        **copy_layer_properties(
            coords, include_opacity=True, include_contrast_limit=False
        ),
        # new layer_name
        "name": f"{coords.name}_expanded",
    }

    return cast("napari.types.LayerDataTuple", (mask, layer_properties, "labels"))
