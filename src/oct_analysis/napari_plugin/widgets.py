"""
Frontend widget code for napari plugin.
The backend functions (oct_analysis.toolkit) are called here with magicgui and error handling decorators.
Magicgui-decorator turns functions into GUI widgets automatically.
Error handling decorator shows error messages (upon exception in backend) in a popup window instead of crashing napari.
The widgets are then assembled into scrollable tabs in __init__.py.
"""

# Python native imports
from pathlib import Path
from functools import partial

# Third party imports
from magicgui import magicgui
from magicgui.widgets import Container, PushButton, Label, FloatSpinBox
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
_current_thresholding_method = None


# Widgets for I/O tab
@magicgui(call_button="Clear Layers")
def clear_layers(viewer: napari.Viewer):
    viewer.layers.clear()
    show_info("Cleared all layers.")


@magicgui(call_button="Load OCT/NIfTI/TIFF files")
@gui_error_handler
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
        metadata=metadata,
        name=f"original ({_filename})",
        visible=False,
    )
    utils.update_layer(viewer, np.copy(stack_norm), name="working copy")

    print(metadata)

    # stack-y apparently napari-x. stack-z apparently napari-y
    update_widget_presets(stack_norm)

    show_info(f"Loaded {_filename} successfully.")


@magicgui(
    call_button="Save Original and Binary",
    save_nifti={
        "widget_type": "CheckBox",
        "text": "Save as NIfTI (.nii.gz)",
        "value": True,
        "enabled": False,
    },
    save_tiff={
        "widget_type": "CheckBox",
        "text": "Save as TIFF (.tiff) [NOT RECOMMENDED]",
        "value": False,
    },
    output_directory={
        "widget_type": "FileEdit",
        "mode": "d",
        "value": str(Path.home()),
    },
)
@gui_error_handler
def save(
    save_nifti,
    save_tiff,
    output_directory,
    viewer: napari.Viewer,
):
    utils.layer_exists_check(viewer, f"original ({_filename})")
    utils.layer_exists_check(viewer, "binary")

    original_layer = viewer.layers[f"original ({_filename})"]
    original_stack = original_layer.data

    binary_stack = viewer.layers["binary"].data

    if save_tiff:
        io.save_as_tiff(
            original_stack, original_layer.metadata, binary_stack, output_directory
        )
        show_info("Saved as TIFF successfully.")

    io.save_as_nifti(
        original_stack, original_layer.metadata, binary_stack, output_directory
    )
    show_info("Saved as NIfTI successfully.")


@magicgui(
    call_button="Export Current Settings as JSON",
    user_handle={"widget_type": "LineEdit", "label": "User handle"},
    output_directory={
        "widget_type": "FileEdit",
        "label": "Output directory",
        "mode": "d",
        "value": str(Path.home()),
    },
)
@gui_error_handler
def export_settings(output_directory, user_handle):
    io.save_settings(
        output_directory,
        user_handle,
        get_setting_widgets(),
        _filename,
        _current_thresholding_method,
    )


@magicgui(call_button="Load settings.json")
@gui_error_handler
def load_settings(viewer: napari.Viewer):
    utils.layer_exists_check(viewer, f"original ({_filename})")

    filepath, _ = QFileDialog.getOpenFileName(
        None, "Select settings file", str(Path.home()), "Format (*.json)"
    )
    if not filepath:
        show_info("No file selected.")
        return

    settings = io.load_settings(Path(filepath))

    # Update the widgets with the loaded settings
    handle = settings.get("user_handle", "")
    export_settings.user_handle.value = handle
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

    show_info(f"Loaded settings from {filepath} for user {handle}")


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
@magicgui(
    call_button="Confirm B-Scan Selection",
    xstart={
        "widget_type": "Slider",
        "min": 0,
        "max": 1000,
        "step": 1,
        "value": 0,
        "label": "First Slice",
    },
    xend={
        "widget_type": "Slider",
        "min": 0,
        "max": 1000,
        "step": 1,
        "value": 1000,
        "label": "Last Slice",
    },
    # slice={'widget_type': 'LineEdit', 'label': 'Input slice number to ignore'}
)
def keep_slices(xstart, xend, viewer: napari.Viewer):
    for lay in viewer.layers:
        visibility_before = lay.visible
        lay.visible = True

        stack = lay.data
        reduced_stack = pre.reduce_stack(stack, xstart, xend)
        lay.data = reduced_stack

        lay.visible = visibility_before

    n_slices = xend - xstart
    keep_slices.xend.max = n_slices
    keep_slices.xstart.max = n_slices
    keep_slices.xstart.value = 0


@magicgui(
    call_button="Locate Window",
    ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 0},
    ymax={"widget_type": "SpinBox", "min": 0, "max": 1001, "step": 1, "value": 100},
    y_offset={"widget_type": "SpinBox", "min": -20, "max": 20, "step": 1, "value": 0},
)
@gui_error_handler
def locate_window(viewer: napari.Viewer, ymin=0, ymax=100, y_offset=0):
    stack = viewer.layers["working copy"].data
    reference_stack = viewer.layers[f"original ({_filename})"].data

    window_coords = pre.locate_window(stack, ymin, ymax, y_offset)
    labels = utils.vizualize_coords(reference_stack, window_coords, pixel_value=1)

    window_coords = {"window_coords": window_coords.tolist()}
    utils.update_layer(
        viewer,
        labels,
        type="label",
        metadata=window_coords,
        name="window_coords",
    )


@magicgui(
    cutoff_y={
        "label": "Manual Window Cutoff",
        "min": 0,
        "max": 300,
        "step": 1,
        "widget_type": "Slider",
    },
    auto_call=True,
)
def mark_cutoff(viewer: napari.Viewer, cutoff_y: int = 0):
    reference_stack = viewer.layers[f"original ({_filename})"].data

    window_coords = pre.get_cutoff(reference_stack, cutoff_y)
    labels = utils.vizualize_coords(reference_stack, window_coords, pixel_value=1)

    window_coords = {"window_coords": window_coords.tolist()}
    utils.update_layer(
        viewer,
        labels,
        type="label",
        metadata=window_coords,
        name="window_coords",
    )


@magicgui(call_button="Zero Out Window")
@gui_error_handler
def zero_out_window(viewer: napari.Viewer):
    utils.layer_exists_check(viewer, "window_coords")

    coords_layer = viewer.layers["window_coords"]
    window_coords = np.array(coords_layer.metadata["window_coords"])
    stack = viewer.layers["working copy"].data

    no_window = pre.zero_out_window(stack, window_coords)

    utils.update_layer(viewer, no_window, name="working copy")
    viewer.layers.remove(coords_layer)


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

    utils.update_layer(viewer, median_filtered, name="working copy")


@magicgui(
    call_button="Enhance Horizontal Edges",
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

    utils.update_layer(viewer, edge_enhanced, name="working copy")


@magicgui(
    call_button="Locate Substratum",
    ymin={"widget_type": "Slider", "min": 0, "max": 1000, "step": 1, "value": 200},
    ymax={"widget_type": "Slider", "min": 0, "max": 1000, "step": 1, "value": 1000},
    y_offset={"widget_type": "SpinBox", "min": -20, "max": 20, "step": 1, "value": 0},
)
@gui_error_handler
def locate_substratum(viewer: napari.Viewer, ymin=0, ymax=1000, y_offset=0):
    stack = viewer.layers["working copy"].data
    reference_stack = viewer.layers[f"original ({_filename})"].data

    substratum_coords = pre.locate_substratum(stack, ymin, ymax, y_offset)
    labels = utils.vizualize_coords(reference_stack, substratum_coords, pixel_value=2)

    substratum_coords = {"substratum_coords": substratum_coords.tolist()}
    utils.update_layer(
        viewer,
        labels,
        type="label",
        metadata=substratum_coords,
        name="substratum_coords",
    )


@magicgui(call_button="Zero Out Substratum")
@gui_error_handler
def zero_out_substratum(viewer: napari.Viewer):
    utils.layer_exists_check(viewer, "substratum_coords")

    coords_layer = viewer.layers["substratum_coords"]
    substratum_coords = np.array(coords_layer.metadata["substratum_coords"])
    stack = viewer.layers["working copy"].data

    no_substratum = pre.zero_out_substratum(stack, substratum_coords)

    utils.update_layer(viewer, no_substratum, name="working copy")
    viewer.layers.remove(coords_layer)


@magicgui(call_button="Confirm Segmentation")
def confirm_segmentation(viewer: napari.Viewer):
    current = viewer.layers["working copy"]
    zeroed_out_stack = current.data
    reference_stack = viewer.layers[f"original ({_filename})"].data

    bin_base_stack = np.where(zeroed_out_stack == 0, 0, reference_stack)

    utils.update_layer(viewer, bin_base_stack, name="working copy")


# Widgets for binarization tab
@magicgui(
    call_button="Increase contrast",
    percentile={
        "widget_type": "FloatSlider",
        "min": 0.0,
        "max": 1,
        "value": 0.1,
    },
)
def increase_contrast(viewer: napari.Viewer, percentile=0.1):
    stack = viewer.layers["working copy"].data

    contrast_enhanced = bin.increase_contrast(stack, percentile)

    utils.update_layer(viewer, contrast_enhanced, name="working copy")


@magicgui(call_button="Auto-Threshold")
def auto_threshold(viewer: napari.Viewer):
    stack = viewer.layers["working copy"].data

    thresholds = bin.get_threshold(stack)

    widget = create_threshold_widget(viewer, thresholds, stack)
    viewer.window.add_dock_widget(widget, name="Threshold Results")


@magicgui(
    call_button="Remove Outliers",
    outlier_size={
        "widget_type": "SpinBox",
        "min": 0,
        "max": 20,
        "step": 1,
        "value": 2,
        "label": "Outlier Size",
    },
)
@gui_error_handler
def remove_outliers(viewer: napari.Viewer, outlier_size=2):
    utils.layer_exists_check(viewer, "binary")

    stack = viewer.layers["binary"].data

    cleaned_binary = bin.rm_outliers(stack, outlier_size)

    viewer.layers["binary"].data = cleaned_binary


@magicgui(call_button="Confirm Binarization")
@gui_error_handler
def confirm_binarization(viewer: napari.Viewer):
    utils.layer_exists_check(viewer, "binary")

    for lay in list(viewer.layers):
        if lay.name not in ["binary", f"original ({_filename})"]:
            viewer.layers.remove(lay)


# Widgets for evaluation tab
@magicgui(call_button="Count Voxels", result_widget=True)
@gui_error_handler
def count_voxels(viewer: napari.Viewer):
    utils.layer_exists_check(viewer, "binary")

    binary_stack = viewer.layers["binary"].data
    voxel_count = eval.voxel_count(binary_stack)

    return voxel_count


# --- Helpers ---


## Create widget list for settings-functionality
def get_setting_widgets() -> list:
    settings_widgets = [  # Needs to be updated if new widgets are added
        keep_slices,
        locate_window,
        mark_cutoff,
        median_filter,
        roi_filter_2D,
        locate_substratum,
        increase_contrast,
        remove_outliers,
    ]

    return settings_widgets


## Update all widget presets with values from loaded stack
def update_widget_presets(stack: np.ndarray):
    global _last_load_path_file

    z, y, x = stack.shape
    (
        z,
        y,
        x,
    ) = z - 1, y - 1, x - 1  # account for python indexing (0 = 1st index)

    # update save paths
    save.output_directory.value = _last_load_path_file
    export_settings.output_directory.value = _last_load_path_file

    # update pre-processing functions limits
    keep_slices.xstart.max = z
    keep_slices.xend.max = z
    keep_slices.xend.value = z
    locate_window.ymin.max = y
    locate_window.ymax.max = y
    locate_window.ymax.value = int(y / 5)
    mark_cutoff.cutoff_y.max = y
    locate_substratum.ymin.max = y
    locate_substratum.ymin.value = y - int(y / 5)
    locate_substratum.ymax.max = y
    locate_substratum.ymax.value = y


## Create widget for thresholding function
def create_threshold_widget(viewer: napari.Viewer, thresholds: dict, stack: np.ndarray):
    container = Container()

    def apply_threshold(stack, viewer, thresh, method_name):
        global _current_thresholding_method
        _current_thresholding_method = method_name
        binary = (stack > thresh).astype(np.uint8)
        binary[stack == 0] = 0
        utils.update_layer(viewer, binary, type="label", name="binary")

    # Auto-threshold fields
    for name, value in thresholds.items():
        lbl = Label(value=f"{name}: {value:.2f}")
        btn = PushButton(text=f"Select {name}")

        btn.changed.connect(partial(apply_threshold, stack, viewer, value, name))

        container.append(lbl)  # type: ignore
        container.append(btn)  # type: ignore

    # Spacer
    container.append(Label(value=""))  # type: ignore

    # User-defined field
    lbl_custom = Label(value="Custom Threshold:")
    spin = FloatSpinBox(min=0.0, max=1.0, step=0.01)
    btn_custom = PushButton(
        text="Select Custom [WARNING: Not suitable for batch processing]"
    )
    btn_custom.changed.connect(
        lambda _: apply_threshold(stack, viewer, spin.value, "custom")
    )

    container.append(lbl_custom)  # type: ignore
    container.append(spin)  # type: ignore
    container.append(btn_custom)  # type: ignore

    return container
