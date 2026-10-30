from typing import TYPE_CHECKING, cast

from magicgui import magic_factory
from numpy import asarray

from ..functions import functions as fn
from ..shared_utility import copy_layer_properties, derive_name
from ._widget_helpers import _run_and_record_action

if TYPE_CHECKING:
    import napari.layers
    import napari.types


@magic_factory(
    call_button="Apply Median Filter",
    kernel_size={
        "min": 1,
        "step": 2,
        "max": 13,
        "tooltip": "Kernel size (odd). Larger values produce stronger smoothing.",
        "label": "Kernel Size",
    },
    image={"label": "Image"},
)
def median_filter_widget(
    image: "napari.layers.Image", kernel_size: int = 1
) -> "napari.types.LayerDataTuple":
    """
    Apply a 2D median filter to each B-Scan of the selected image.
    A median filter replaces each pixel with the median value of its neighborhood.
    The 'size' parameter determines the size of the neighborhood (must be odd so it has a single center pixel).
    Median filters are effective at removing noise while preserving edges.
    """
    output_name = derive_name(image.name, "median")

    params = {"kernel_size": kernel_size}
    data = _run_and_record_action(
        func=fn.median_filter,
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


@magic_factory(
    call_button="Apply Gaussian Filter",
    sigma={
        "max": 20.0,
        "tooltip": "Standard deviation of Gaussian kernel. Higher values blur more.",
        "label": "Sigma",
    },
    image={"label": "Image"},
)
def gaussian_filter_widget(
    image: "napari.layers.Image", sigma: float = 0.0
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(image.name, "gauss")

    params = {"sigma": sigma}
    data = _run_and_record_action(
        func=fn.gaussian_filter,
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


@magic_factory(
    call_button="Apply Sobel Filter",
    image={"label": "Image"},
)
def sobel_filter_widget(
    image: "napari.layers.Image",
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(image.name, "sobel")

    params = {}
    data = _run_and_record_action(
        func=fn.sobel_filter,
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


@magic_factory(
    call_button="Remove Small Objects",
    max_object_size={
        "label": "Max Object Size",
        "min": 0,
        "tooltip": "Maximum size of connected components (in pixels) to remove.",
    },
)
def remove_small_objects_widget(
    labels: "napari.layers.Labels", max_object_size: int = 0
) -> "napari.types.LayerDataTuple":
    output_name = derive_name(labels.name, "cleaned")

    params = {"max_object_size": max_object_size}
    data = _run_and_record_action(
        func=fn.remove_small_objects,
        inputs={"labels": asarray(labels.data)},
        input_layers={"labels": labels.name},
        output_layer=output_name,
        params=params,
    )

    layer_properties = {
        **copy_layer_properties(
            labels, include_opacity=True, include_contrast_limit=False
        ),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, layer_properties, "labels"))
