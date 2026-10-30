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
    call_button="Zero Out Area",
    direction={
        "choices": ["above", "below"],
        "label": "Direction",
        "tooltip": "Choose whether to zero areas above or below the substratum labels.",
    },
    image={"label": "Image"},
)
def zero_out_area_widget(
    image: "napari.layers.Image",
    surface_coords: "napari.layers.Labels",
    direction: Literal["above", "below"] = "below",
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(image.name, "zeroed")

    params = {"direction": direction}
    data = _run_and_record_action(
        func=fn.zero_out_area,
        inputs={
            "image": asarray(image.data),
            "surface_coords": asarray(surface_coords.data),
        },
        input_layers={"image": image.name, "surface_coords": surface_coords.name},
        output_layer=output_name,
        params=params,
    )

    layer_properties = {
        **copy_layer_properties(image, include_opacity=True),
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, layer_properties, "image"))


@magic_factory(
    call_button="Replace Reflection",
    image={"label": "Image"},
    reflection={"label": "Reflection"},
    axial_offset={
        "label": "Axial Offset",
        "min": -500,
        "max": 500,
        "tooltip": "Axial offset from reflection [px] to use for replacement values.",
    },
    axial_padding={
        "label": "Axial Padding",
        "tooltip": "Padding (thickness) used when replacing reflection regions.",
    },
)
def replace_reflection_widget(
    image: "napari.layers.Image",
    reflection: "napari.layers.Labels",
    axial_offset: int = 5,
    axial_padding: int = 2,
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(image.name, "reflection_removed")

    params = {"axial_offset": axial_offset, "axial_padding": axial_padding}
    data = _run_and_record_action(
        func=fn.replace_reflection,
        inputs={
            "image": asarray(image.data),
            "reflection": asarray(reflection.data),
        },
        input_layers={"image": image.name, "reflection": reflection.name},
        output_layer=output_name,
        params=params,
    )

    layer_properties = {
        **copy_layer_properties(image, include_opacity=True),
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, layer_properties, "image"))
