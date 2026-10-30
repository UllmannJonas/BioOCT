from typing import TYPE_CHECKING, cast

# Third party imports
from magicgui import magic_factory
from numpy import asarray

# Local imports
from ..functions import functions as fn
from ..shared_utility import copy_layer_properties, derive_name
from ._widget_helpers import _get_napari_image_class, _run_and_record_action

if TYPE_CHECKING:
    import napari.layers
    import napari.types


@magic_factory(
    call_button="Untilt Image",
    image={"label": "Image"},
    substratum_coords={"label": "Substratum Coords"},
)
def untilt_widget(
    image: "napari.layers.Layer", substratum_coords: "napari.layers.Labels"
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(image.name, "untilted")

    params = {}
    data = _run_and_record_action(
        func=fn.untilt,
        inputs={
            "image": asarray(image.data),
            "substratum_coords": asarray(substratum_coords.data),
        },
        input_layers={"image": image.name, "substratum_coords": substratum_coords.name},
        output_layer=output_name,
        params=params,
    )

    is_image = isinstance(image, _get_napari_image_class())
    layer_properties = {
        **copy_layer_properties(
            image,
            include_opacity=True,
            include_contrast_limit=not is_image,
        ),
        "name": output_name,
    }

    layer_type = image._type_string

    return cast("napari.types.LayerDataTuple", (data, layer_properties, layer_type))
