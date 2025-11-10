"""
Frontend widget code for napari plugin.
The backend functions (oct_analysis.toolkit) are called here with magicgui and error handling decorators.
Magicgui-decorator turns functions into GUI widgets automatically.
Error handling decorator shows error messages (upon exception in backend) in a popup window instead of crashing napari.
The widgets are then assembled into scrollable tabs in __init__.py.
"""

# Python native imports
from pathlib import Path
from typing import Optional

# Third party imports
from magicgui import magicgui
import napari
from napari.utils.notifications import show_info
import numpy as np
from qtpy.QtWidgets import QFileDialog

# Local imports
from oct_analysis.toolkit import utils, io, pre, bin, eval
from oct_analysis.toolkit.utils import gui_error_handler


# Initialize globals
_last_load_path_file = str(Path.home())  # path remembering
_filename = ""


# Widgets for I/O tab
@magicgui(call_button="Clear Layers")
def clear_layers(viewer: napari.Viewer):
    viewer.layers.clear()
    show_info("Cleared all layers.")


@magicgui(call_button="Load OCT/NIfTI/TIF")
def load_file(viewer: napari.Viewer):
    global _last_load_path_file

    filepath, _ = QFileDialog.getOpenFileName(
        None,
        "Select file",
        _last_load_path_file,
        "Format (*.oct *.nii *.nii.gz *niigz *tif *tiff)",
    )
    if not filepath:
        show_info("No file selected.")
        return

    _last_load_path_file = str(Path(filepath).parent)  # Save path for next use

    load_fn = io.get_load_fn(Path(filepath))

    stack, metadata = load_fn(Path(filepath))

    global _filename
    _filename = metadata["filename"]

    stack_norm = io.normalize(stack)
    utils.update_layer(
        viewer,
        stack_norm,
        type="image",
        metadata=metadata,
        name="original",
        visible=True,
    )
    utils.update_layer(
        viewer,
        stack_norm,
        type="image",
        name="working copy",
        visible=True,
    )

    #! Napari X, Y and Z axes do not correspond to X, Y and Z axes of the OCT file!
    # Update GUI widget values with the actual size of the OCT images
    x_max = metadata.get("size_px", {}).get("y", 1000) - 1
    ignore_slices.xend.max = x_max
    y_max = metadata.get("size_px", {}).get("z", 1000) - 1
    locate_window.ymin.max = y_max - 1
    locate_window.ymax.max = y_max
    locate_substratum.ymin.max = y_max - 1
    locate_substratum.ymax.max = y_max
    locate_substratum.ymax.value = y_max

    show_info(f"Loaded {_filename} successfully.")


@magicgui(
    input_text={"widget_type": "LineEdit", "label": "User handle"},
    auto_call=True,  # Funktion wird bei jeder Änderung aufgerufen
)
def handle_input(input_text: str):
    return input_text


@magicgui(
    call_button="Save Original & Binary",
    file_format={
        "widget_type": "ComboBox",
        "choices": [".nii.gz", ".nii", ".niigz", ".tif", ".tiff"],
        "value": ".nii.gz",
        "label": "File Format",
    },
    output_directory={
        "widget_type": "FileEdit",
        "mode": "d",
        "value": str(Path.home()),
    },
    save_settings={"widget_type": "CheckBox", "text": "Save settings", "value": True},
    settings_directory={
        "widget_type": "FileEdit",
        "mode": "d",
        "value": str(Path.home()),
    },
)
def save(
    file_format,
    output_directory,
    save_settings,
    settings_directory,
    viewer: napari.Viewer,
):
    original_layer = viewer.layers["original"]
    if original_layer is not None:
        original_stack = original_layer.data
        metadata = original_layer.metadata.get("original")
    else:
        show_info("Original layer not found. Please load an OCT file first.")
        return

    binary_stack = viewer.layers["binary"].data

    save_fn = io.get_save_fn(original_stack, metadata, file_format)
    if save_fn(original_stack, metadata, binary_stack, output_directory):
        viewer.layers.clear()
        if save_settings:
            handle = handle_input.input_text.value.strip()
            if io.save_settings(
                settings_directory,
                handle,
                setting_widgets=get_setting_widgets(),
                stack_metadata=metadata,
            ):
                show_info(
                    f"Saved stack and binary mask to {output_directory} and settings to {settings_directory}"
                )
        else:
            show_info(f"Saved stack and binary mask to {output_directory})")


@gui_error_handler
@magicgui(call_button="Load settings.json")
def load_settings(viewer: napari.Viewer):
    if "original" not in viewer.layers:
        show_info("OCT File has to be loaded before loading settings.")
        return

    filepath, _ = QFileDialog.getOpenFileName(
        None, "Select settings file", str(Path.home()), "Format (*.json)"
    )
    if not filepath:
        show_info("No file selected.")
        return

    settings = io.load_settings(Path(filepath))
    if not settings:
        show_info("No valid settings found in the file.")
        return

    # Update the widgets with the loaded settings
    user_handle = settings.get("handle_input", {}).get("input_text", "")
    handle_input.input_text.value = user_handle
    median_filter.filter_size.value = settings.get("median_filter", {}).get(
        "filter_size", 3
    )
    roi_filter_2D.roi_size.value = settings.get("roi_filter_2D", {}).get("roi_size", 5)
    locate_window.ymin.value = settings.get("locate_window", {}).get("ymin", 0)
    locate_window.ymax.value = settings.get("locate_window", {}).get("ymax", 100)
    locate_window.y_offset.value = settings.get("locate_window", {}).get("y_offset", 0)
    locate_substratum.ymin.value = settings.get("locate_substratum", {}).get(
        "ymin", 200
    )
    locate_substratum.ymax.value = settings.get("locate_substratum", {}).get(
        "ymax", 1000
    )
    locate_substratum.y_offset.value = settings.get("locate_substratum", {}).get(
        "y_offset", 0
    )
    increase_contrast.percentile.value = settings.get("increase_contrast", {}).get(
        "percentile", 0.5
    )

    show_info(f"Loaded settings from {filepath} for user {user_handle}")


"""
@magicgui(call_button="Apply current settings to current stack")
def apply_loaded_settings_single(viewer: napari.Viewer):
    if "base" not in viewer.layers:
        show_info("Load an OCT file first.")
        return

    # Apply the settings to the current stack
    median_filter(viewer=viewer)
    roi_filter_2D(viewer=viewer)
    locate_window(viewer=viewer)
    zero_out_window(viewer=viewer)
    locate_substratum(viewer=viewer)
    zero_out_substratum(viewer=viewer)
    increase_contrast(viewer=viewer)
    remove_outliers(viewer=viewer)

    show_info("Applied loaded settings to the current stack.")


@magicgui(call_button="Apply current settings to multiple files")
def apply_loaded_settings_bulk(viewer: napari.Viewer):
    filepaths, _ = QFileDialog.getOpenFileNames(
        None, "Select files", "", "Format (*.oct *.nii *.nii.gz *niigz *tif *tiff)"
    )
    if not filepaths:
        show_info("No files selected.")
        return
    for (
        filepath
    ) in filepaths:  # Sequentially load each file, apply auto labeling and save
        load_file(filepath=filepath, viewer=viewer)
        apply_loaded_settings_single(viewer=viewer)
        show_info("Check console for user input.")
        user_input = input(
            "Continue with current settings with 'y' \nAbort with 'stop' \n"
        )
        if user_input.lower() == "stop":
            show_info("Aborted.")
            return
        save(
            file_format=save.file_format.value,
            output_directory=save.output_directory.value,
            save_settings=False,
            settings_directory=save.settings_directory.value,
            viewer=viewer,
        )
"""


# Widgets for pre-processing tab
#! TBD if keep this
@magicgui(
    call_button="Ignore Slices",
    xstart={
        "widget_type": "SpinBox",
        "min": 0,
        "max": 1000,
        "step": 1,
        "value": 0,
        "label": "First Slice",
    },
    xend={
        "widget_type": "SpinBox",
        "min": 0,
        "max": 1000,
        "step": 1,
        "value": 1000,
        "label": "Last Slice",
    },
    # slice={'widget_type': 'LineEdit', 'label': 'Input slice number to ignore'}
)
def ignore_slices(xstart, xend, viewer: napari.Viewer):
    stack = viewer.layers["working copy"].data

    if xstart > xend or xend > stack.shape[0]:
        show_info("Invalid slice range.")
        return

    slices = list(range(xstart, xend + 1))
    modified_stack = pre.zero_out_ignored_slices(stack, slices)

    utils.update_layer(
        viewer, modified_stack, type="image", name="base_reduced", visible=False
    )


@magicgui(
    call_button="Apply Median Filter",
    filter_size={
        "widget_type": "SpinBox",
        "min": 1,
        "max": 7,
        "step": 2,
        "value": 3,
        "label": "Filter Size",
    },
)
def median_filter(viewer: napari.Viewer, filter_size=3):
    stack = viewer.layers["working copy"].data

    median_filtered = pre.median_blur(stack, filter_size)

    utils.update_layer(
        viewer, median_filtered, type="image", name="working copy", visible=True
    )

    #! Keep or remove?
    if "bin_base" in viewer.layers:
        show_info(
            "Target layer updated. Reapply >>Zero Out Substratum<< to update bin_base layer."
        )


@magicgui(
    call_button="Enhance horizontal Edges",
    roi_size={
        "widget_type": "SpinBox",
        "min": 1,
        "max": 21,
        "step": 2,
        "value": 5,
        "label": "Filter Size",
    },
)
def roi_filter_2D(viewer: napari.Viewer, roi_size=5):
    stack = viewer.layers["working copy"].data

    edge_enhanced = pre.roi_filter_2D(stack, roi_size)

    utils.update_layer(
        viewer, edge_enhanced, type="image", name="working copy", visible=False
    )


@magicgui(
    call_button="Locate Window",
    ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 0},
    ymax={"widget_type": "SpinBox", "min": 0, "max": 1001, "step": 1, "value": 100},
    y_offset={"widget_type": "SpinBox", "min": -100, "max": 100, "step": 1, "value": 0},
)
def locate_window(viewer: napari.Viewer, ymin=0, ymax=100, y_offset=0):
    if ymin >= ymax:
        show_info("ymin must be less than ymax.")
        return

    stack = viewer.layers["target"].data
    reference_stack = viewer.layers["original"].data

    window_coords = pre.locate_window(stack, ymin, ymax, y_offset)

    labels = utils.vizualize_coords(reference_stack, window_coords, pixel_value=1)

    utils.update_layer(
        viewer,
        labels,
        type="label",
        metadata=window_coords,
        name="window_coords",
        visible=True,
    )


@magicgui(call_button="Zero Out Window")
def zero_out_window(viewer: napari.Viewer):
    if "window_coords" not in viewer.layers:
        show_info("Window has to be located first.")
        return

    coords_layer = viewer.layers["window_coords"]
    window_coords = coords_layer.metadata.get("window_coords")
    stack = viewer.layers["working copy"].data

    no_window = pre.zero_out_window(stack, window_coords)

    utils.update_layer(
        viewer, no_window, type="image", name="working copy", visible=True
    )
    viewer.layers.remove(coords_layer)

    #! wth is binbase
    if "bin_base" in viewer.layers:
        show_info(
            "Target layer updated. Reapply >>Zero Out Substratum<< to update bin_base layer."
        )


@magicgui(
    call_button="Locate Substratum",
    ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 200},
    ymax={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 1000},
    y_offset={"widget_type": "SpinBox", "min": -100, "max": 100, "step": 1, "value": 0},
)
def locate_substratum(viewer: napari.Viewer, ymin=0, ymax=1000, y_offset=0):
    if ymin >= ymax:
        show_info("ymin must be less than ymax.")
        return

    stack = viewer.layers["working copy"].data
    reference_stack = viewer.layers["original"].data

    substratum_coords = pre.locate_substratum(stack, ymin, ymax, y_offset)
    labels = utils.vizualize_coords(reference_stack, substratum_coords, pixel_value=2)

    utils.update_layer(
        viewer,
        labels,
        type="label",
        metadata=substratum_coords,
        name="substratum_coords",
        visible=True,
    )


@magicgui(call_button="Zero Out Substratum")
def zero_out_substratum(viewer: napari.Viewer):
    if "substratum_coords" not in viewer.layers:
        show_info("Substratum has to be located first.")
        return

    coords_layer = viewer.layers["substratum_coords"]
    substratum_coords = coords_layer.metadata.get("substratum_coords")
    stack = viewer.layers["working copy"].data

    no_substratum = pre.zero_out_substratum(stack, substratum_coords)

    utils.update_layer(
        viewer, no_substratum, type="image", name="working copy", visible=True
    )
    viewer.layers.remove(coords_layer)


# Widgets for binarization tab
@magicgui(
    call_button="Increase contrast",
    percentile={
        "widget_type": "FloatSpinBox",
        "min": 0.0,
        "max": 10.0,
        "step": 0.1,
        "value": 0.5,
    },
    show_histograms={
        "widget_type": "CheckBox",
        "text": "Show histograms",
        "value": False,
    },
)
def increase_contrast(viewer: napari.Viewer, percentile=0.5, show_histograms=False):
    stack = viewer.layers["working copy"].data

    contrast_enhanced = bin.increase_contrast(stack, percentile)
    if show_histograms:
        bin.plot_histograms(stack, contrast_enhanced, percentile)

    utils.update_layer(
        viewer, contrast_enhanced, type="image", name="working copy", visible=True
    )


@magicgui(call_button="Auto-Threshold", result_widget=True)
def auto_threshold(viewer: napari.Viewer, thresh: Optional[float] = None) -> float:
    stack = viewer.layers["working copy"].data

    if thresh is None:
        thresh = bin.get_threshold(stack)

    binary = (stack > thresh).astype(np.uint8)
    binary[stack == 0] = 0  # Keep zero pixels as zero

    utils.update_layer(viewer, binary, type="image", name="binary", visible=True)

    return thresh


# @magicgui(
#     threshold={
#         "widget_type": "FloatSpinBox",
#         "min": 0.0,
#         "max": 1.0,
#         "step": 0.001,
#         "value": 0.700,
#         "label": "Threshold",
#     },
#     auto_call=True,
# )
# def binarize(viewer: napari.Viewer, threshold=0.7):
#     if "bin_base" not in viewer.layers:
#         show_info("Use >>Increase Contrast<< first.")
#         return

#     stack = viewer.layers["bin_base"].data

#     # TODO: finetuning threshold toggle nur auf aktuellem slice
#     binary = (stack > threshold).astype(np.uint8)

#     if "binary" in viewer.layers:
#         viewer.layers["binary"].data = binary
#     else:
#         viewer.add_labels(binary, name="binary", visible=True)

#     for lay in viewer.layers:
#         lay.visible = False
#     viewer.layers["binary"].visible = True
#     viewer.layers["binary"].opacity = 0.8
#     viewer.layers["bin_base"].visible = True


@magicgui(
    call_button="Apply",
    outlier_size={
        "widget_type": "SpinBox",
        "min": 0,
        "max": 20,
        "step": 1,
        "value": 2,
        "label": "Outlier Size",
    },
)
def remove_outliers(viewer: napari.Viewer, outlier_size=2):
    if "binary" not in viewer.layers:
        show_info("Binarize first.")
        return

    stack = viewer.layers["binary"].data

    cleaned_binary = bin.rm_outliers(stack, outlier_size)

    viewer.layers["binary"].data = cleaned_binary


@magicgui(call_button="Confirm Binarization")
def confirm_binarization(viewer: napari.Viewer):
    if "binary" not in viewer.layers:
        show_info("Binarize first.")
        return

    for lay in list(viewer.layers):
        if lay.name not in ["binary", "original"]:
            viewer.layers.remove(lay)


# Widgets for evaluation tab
@magicgui(call_button="Count Voxels", result_widget=True)
def count_voxels(viewer: napari.Viewer):
    if "binary" not in viewer.layers:
        show_info("Binarized layer is required.")
        return

    binary_stack = viewer.layers["binary"].data
    voxel_count = eval.voxel_count(binary_stack)

    return voxel_count


# Helpers


## Create widget list for settings
def get_setting_widgets() -> list:
    settings_widgets = [  # Needs to be updated if new widgets are added
        handle_input,
        median_filter,
        roi_filter_2D,
        locate_window,
        locate_substratum,
        increase_contrast,
        auto_threshold,
        remove_outliers,
    ]

    return settings_widgets
