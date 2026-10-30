from typing import TYPE_CHECKING

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
    call_button="Export to TIFF",
    image={"label": "Image"},
)
def export_to_tiff_widget(image: "napari.layers.Layer") -> None:
    params = {
        "spacing": image.metadata[
            "spacing"
        ],  # * should stay the same for a batch -> keep static in record+replay
        "output_filename": "{input_layer}.tiff",
    }
    _run_and_record_action(
        func=fn.export_to_tiff,
        inputs={"image": asarray(image.data)},
        input_layers={"image": image.name},
        output_layer=None,
        params=params,
        resolve_path=lambda name: resolve_output_path(name, image),
    )


@magic_factory(
    call_button="Export to NIfTI",
    image={"label": "Image"},
)
def export_to_nifti_widget(image: "napari.layers.Layer") -> None:
    params = {
        "affine": image.affine.affine_matrix.tolist(),  # * should stay the same for a batch -> keep static in record+replay
        "output_filename": "{input_layer}.nii.gz",
    }
    _run_and_record_action(
        func=fn.export_to_nifti,
        inputs={"image": asarray(image.data)},
        input_layers={"image": image.name},
        output_layer=None,
        params=params,
        resolve_path=lambda name: resolve_output_path(name, image),
    )
