from typing import TYPE_CHECKING, Literal, cast

# Third party imports
from magicgui import magic_factory
from numpy import asarray

# Local imports
from ..functions import functions as fn
from ..shared_utility import copy_layer_properties, derive_name
from ._widget_helpers import _run_and_record_action

if TYPE_CHECKING:
    import napari.layers
    import napari.types


@magic_factory(
    call_button="Enhance Contrast",
    image={"label": "Image"},
    method={"label": "Method", "tooltip": "Select contrast enhancement method."},
    gamma={
        "label": "Gamma",
        "min": 0.1,
        "step": 0.1,
        "tooltip": "Gamma value for nonlinear brightness adjustment.",
    },
    clip_low_pct={
        "label": "Clip Low [%]",
        "min": 0.0,
        "max": 100.0,
        "step": 0.1,
        "tooltip": "Lower histogram percentile to clip for contrast stretching.",
    },
    clip_high_pct={
        "label": "Clip High [%]",
        "min": 0.0,
        "max": 100.0,
        "step": 0.1,
        "tooltip": "Upper histogram percentile to clip for contrast stretching.",
    },
    clahe_clip_limit={
        "label": "CLAHE Clip Limit",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
        "tooltip": "CLAHE clip limit; larger values increase local contrast but may amplify noise.",
    },
    clahe_tile_size={
        "label": "CLAHE Tile Size",
        "min": 1,
        "max": 64,
        "step": 1,
        "tooltip": "Size of local regions for CLAHE. Smaller tiles increase local detail.",
    },
)
def enhance_contrast_widget(
    image: "napari.layers.Image",
    method: Literal["gamma", "clip", "clahe"] = "gamma",
    gamma: float = 1.0,
    clip_low_pct: float = 1.0,
    clip_high_pct: float = 99.0,
    clahe_clip_limit: float = 2.0,
    clahe_tile_size: int = 8,
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(image.name, "enhanced")

    params = {
        "method": method,
        **({"gamma": gamma} if method == "gamma" else {}),
        **({"clip_low_pct": clip_low_pct} if method == "clip" else {}),
        **({"clip_high_pct": clip_high_pct} if method == "clip" else {}),
        **({"clahe_clip_limit": clahe_clip_limit} if method == "clahe" else {}),
        **({"clahe_tile_size": clahe_tile_size} if method == "clahe" else {}),
    }
    data = _run_and_record_action(
        func=fn.enhance_contrast,
        inputs={"image": asarray(image.data)},
        input_layers={"image": image.name},
        output_layer=output_name,
        params=params,
    )

    layer_properties = {
        **copy_layer_properties(image, include_opacity=True),
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, layer_properties, "image"))


# * Enhance contrast widget initialization which connects a callback to the method dropdown to show/hide related parameters
def _init_enhance_contrast_widget(widget):
    def _on_method_change(value):
        widget.gamma.visible = False
        widget.clip_low_pct.visible = False
        widget.clip_high_pct.visible = False
        widget.clahe_clip_limit.visible = False
        widget.clahe_tile_size.visible = False

        if value == "gamma":
            widget.gamma.visible = True
        elif value == "clip":
            widget.clip_low_pct.visible = True
            widget.clip_high_pct.visible = True
        elif value == "clahe":
            widget.clahe_clip_limit.visible = True
            widget.clahe_tile_size.visible = True

    widget.method.changed.connect(_on_method_change)
    _on_method_change(widget.method.value)


enhance_contrast_widget._widget_init = _init_enhance_contrast_widget
