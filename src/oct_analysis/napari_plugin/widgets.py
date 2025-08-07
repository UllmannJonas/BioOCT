from cProfile import label
from magicgui import magicgui
import napari
from napari.utils.notifications import show_info
import numpy as np
from qtpy.QtWidgets import QFileDialog
from pathlib import Path
import webbrowser

from oct_analysis.octools import processing_functions as ip

@magicgui(call_button="Open Instructions")
def show_instructions():
    webbrowser.open("https://github.com/AndreasNetsch/oct_analysis")
    show_info("Instructions opened in your browser.")

@magicgui(call_button="Load OCT/NIfTI/TIF")
def load(viewer: napari.Viewer):
    filepath, _ = QFileDialog.getOpenFileName(None, 'Select file', '', 'Format (*.oct *.nii *.nii.gz *niigz *tif *tiff)') # type: ignore
    if not filepath:
        show_info("No file selected.")
        return # Abort
    
    load_fn = ip.get_load_fn(Path(filepath))

    stack, metadata = load_fn(Path(filepath))

    if stack is not None:   #If file is loaded correctly
        viewer.layers.clear()   #Clear existing layers to prevent duplicate naming (i.g. normalized[1])

    original_layer = viewer.add_image(stack, name=f'{metadata["filename"]} (Original)', visible=False)
    original_layer.metadata['oct_metadata'] = metadata # type: ignore

    stack_norm = ip._normalize(stack)
    viewer.add_image(stack_norm, name='base', visible=True)

    y_max = metadata.get('size_px', {}).get('z', 1000) -1 # Update maximum slider values with the actual size of the OCT images
    locate_window.ymin.max = y_max -1
    locate_window.ymax.max = y_max
    locate_substratum.ymin.max = y_max -1
    locate_substratum.ymax.max = y_max
    locate_substratum.ymax.value = y_max

    show_info(f"Loaded {metadata['filename']}")


@magicgui(
            call_button="Apply Median Filter",
            filter_size={"widget_type": "SpinBox", "min": 1, "max": 7, "step": 2, "value": 3, "label": "Filter Size"}
    )
def median_filter(filter_size, viewer: napari.Viewer):
    if 'base' not in viewer.layers:
        show_info("OCT File has to be loaded.")
        return

    stack = viewer.layers['base'].data

    median_filtered = ip.median_blur(stack, filter_size)

    if 'target' in viewer.layers:
        viewer.layers['target'].data = median_filtered
    else:
        viewer.add_image(median_filtered, name='target', visible=True)


@magicgui(call_button="Enhance horizontal Edges",
            roi_size={"widget_type": "SpinBox", "min": 1, "max": 21, "step": 2, "value": 5, "label": "Filter Size"}
)
def roi_filter_2D(roi_size, viewer: napari.Viewer):
    if 'target' not in viewer.layers:
        show_info("Median Filter has to be applied first.")
        return
    if 'target' not in viewer.layers:
        show_info("Median Filter has to be applied first.")
        return
    
    stack = viewer.layers['target'].data

    edge_enhanced = ip.roi_filter_2D(stack, roi_size)

    if 'edge_enhanced' in viewer.layers:
        viewer.layers['edge_enhanced'].data = edge_enhanced
    else:
        viewer.add_image(edge_enhanced, name="edge_enhanced", visible=False)

@magicgui(call_button="Locate Window",
            ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 0},
            ymax={"widget_type": "SpinBox", "min": 0, "max": 1001, "step": 1, "value": 100},
            y_offset={"widget_type": "SpinBox", "min": -100, "max": 100, "step": 1, "value": 0}
)
def locate_window(ymin, ymax, y_offset, viewer: napari.Viewer):
    if 'edge_enhanced' not in viewer.layers:
        show_info("ROI filter has to be applied first.")
        return
    if ymin >= ymax:
        show_info("ymin must be less than ymax.")
        return
    
    working_stack = viewer.layers['edge_enhanced'].data
    reference_stack = viewer.layers['base'].data

    window_coords = ip.locate_window(working_stack, ymin, ymax, y_offset)
    label_stack = viz_coords(reference_stack, window_coords, pixel_value=1)

    if 'window_coords' in viewer.layers:
        coords_layer = viewer.layers['window_coords']
        coords_layer.data = label_stack
    else:
        coords_layer = viewer.add_labels(label_stack, name='window_coords', visible=True)
    
    coords_layer.metadata['window_coords'] = window_coords

@magicgui(call_button="Zero Out Window")
def zero_out_window(viewer: napari.Viewer):
    if 'window_coords' not in viewer.layers:
        show_info("Window has to be located first.")
        return
    window_coords = viewer.layers['window_coords'].metadata.get('window_coords')
    target_stack = viewer.layers['target'].data

    no_window = ip.zero_out_window(target_stack, window_coords) # type: ignore


    viewer.layers['target'].data = no_window

    coords_layer = viewer.layers['window_coords']
    viewer.layers.remove(coords_layer)

@magicgui(call_button="Locate Substratum",
            ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 200},
            ymax={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 1000},
            y_offset={"widget_type": "SpinBox", "min": -100, "max": 100, "step": 1, "value": 0}
)
def locate_substratum(ymin, ymax, y_offset, viewer: napari.Viewer):
    if 'edge_enhanced' not in viewer.layers:
        show_info("ROI filter has to be applied first.")
        return
    if ymin >= ymax:
        show_info("ymin must be less than ymax.")
        return
    
    working_stack = viewer.layers['edge_enhanced'].data
    reference_stack = viewer.layers['base'].data

    substratum_coords = ip.locate_substratum(working_stack, ymin, ymax, y_offset)
    label_stack = viz_coords(reference_stack, substratum_coords, pixel_value=2)

    if 'substratum_coords' in viewer.layers:
        coords_layer = viewer.layers['substratum_coords']
        coords_layer.data = label_stack
    else:
        coords_layer = viewer.add_labels(label_stack, name="substratum_coords", visible=True)
    
    coords_layer.metadata['substratum_coords'] = substratum_coords

@magicgui(call_button="Zero Out Substratum")
def zero_out_substratum(viewer: napari.Viewer):
    if 'target' not in viewer.layers:
        show_info("Create target layer first.")
        return
    if 'substratum_coords' not in viewer.layers:
        show_info("Substratum has to be located first.")
        return
    substratum_coords = viewer.layers['substratum_coords'].metadata.get('substratum_coords')
    target_stack = viewer.layers['target'].data

    no_substratum = ip.zero_out_substratum(target_stack, substratum_coords) # type: ignore

    viewer.layers['target'].data = no_substratum

    coords_layer = viewer.layers['substratum_coords']
    edge_enhanced_layer = viewer.layers['edge_enhanced']
    viewer.layers.remove(coords_layer)
    viewer.layers.remove(edge_enhanced_layer)

@magicgui(call_button="Increase contrast",
    percentile={"widget_type": "FloatSpinBox", "min": 0.0, "max": 10.0, "step": 0.1, "value": 0.5},
    show_histograms={"widget_type": "CheckBox", "text": "Show histograms", "value": False},
)
def increase_contrast(percentile, show_histograms, viewer: napari.Viewer):
    if 'target' not in viewer.layers:
        show_info("Create target layer first.")
        return

    stack = viewer.layers['target'].data
    
    contrast_enhanced = ip.increase_contrast(stack, percentile)
    if show_histograms:
        ip.plot_histograms(stack, contrast_enhanced, percentile)

    if 'bin_base' in viewer.layers:
        viewer.layers['bin_base'].data = contrast_enhanced
    else:
        viewer.add_image(contrast_enhanced, name="bin_base", visible=True)

    for lay in viewer.layers:
        lay.visible = False
    viewer.layers['bin_base'].visible = True

@magicgui(
    threshold={'widget_type': 'FloatSpinBox', 'min': 0.0, 'max': 1.0, 'step': 0.001, 'value': 0.7, 'label': 'Threshold'},
    auto_call=True
)
def binarize(threshold, viewer: napari.Viewer):
    if 'bin_base' not in viewer.layers:
        show_info("Use >>Increase Contrast<< first.")
        return

    stack = viewer.layers['bin_base'].data

    # TODO: finetuning threshold toggle nur auf aktuellem slice
    binary = (stack > threshold).astype(np.uint8)

    if 'binary' in viewer.layers:
        viewer.layers['binary'].data = binary
    else:
        viewer.add_labels(binary, name="binary", visible=True)

    for lay in viewer.layers:
        lay.visible = False
    viewer.layers['binary'].visible = True
    viewer.layers['binary'].opacity = 0.5
    viewer.layers['base'].visible = True

@magicgui(
        outlier_size={'widget_type': 'SpinBox', 'min': 0, 'max': 100, 'step': 1, 'value': 2, 'label': 'Outlier Size'},
        auto_call=True
)
def remove_outliers(outlier_size, viewer: napari.Viewer):
    if 'binary' not in viewer.layers:
        show_info("Binarize first by adjusting threshold.")
        return
    stack = viewer.layers['binary'].data

    cleaned_binary = ip.rm_outliers(stack, outlier_size)

    viewer.layers['binary'].data = cleaned_binary

@magicgui(call_button="Confirm Binarization")
def confirm_binarization(viewer: napari.Viewer):
    if 'binary' not in viewer.layers:
        show_info("Adjust threshold first.")
        return
    for lay in list(viewer.layers):
        if not (lay.name == "binary" or "Original" in lay.name):
            viewer.layers.remove(lay)

@magicgui(
    input_text={'widget_type': 'LineEdit', 'label': 'User handle'},
    auto_call=True  # Funktion wird bei jeder Änderung aufgerufen
)
def handle_input(input_text: str):
    return input_text


setting_widgets = [ #Needs to be updated if new widgets are added
    handle_input,
    median_filter,
    roi_filter_2D,
    increase_contrast,
    binarize,
    remove_outliers
]

@magicgui(
        call_button='Save Original & Binary',
        file_format={"widget_type": "ComboBox", "choices": ['.nii.gz', '.nii', '.niigz', '.tif', '.tiff'], "value": ".nii.gz", "label": "File Format"},
        output_directory={"widget_type": "FileEdit", "mode": "d", "value": str(Path.home())},
        save_settings={"widget_type": "CheckBox", "text": "Save settings", "value": True},
        settings_directory={"widget_type": "FileEdit", "mode": "w", "value": str(Path.home() / "settings.json")}
)
def save(file_format, output_directory, save_settings, settings_directory, viewer: napari.Viewer):
    original_layer = next((layer for layer in viewer.layers if "Original" in layer.name), None)
    if original_layer is not None:
        original_stack = original_layer.data
        metadata = original_layer.metadata.get('oct_metadata')
    else:
        show_info("Original layer not found. Please load an OCT file first.")
        return
    binary_stack = viewer.layers['binary'].data

    if (ip.get_save_fn(original_stack, metadata, file_format))(original_stack, metadata, binary_stack, output_directory): # type: ignore
        viewer.layers.clear()
        if save_settings:
            if ip.save_settings(settings_directory, handle_input.input_text.value.strip(), setting_widgets, metadata): # type: ignore
                show_info(f"Saved stack and binary mask to {output_directory} and settings to {settings_directory}")
        else:
            show_info(f"Saved stack and binary mask to {output_directory})")


@magicgui(call_button="Count Voxels")
def count_voxels(viewer: napari.Viewer):
    if 'binary' not in viewer.layers:
        show_info("Binarized layer is required.")
        return
    
    binary_stack = viewer.layers['binary'].data
    voxel_count = ip.voxel_count(binary_stack)

    show_info(f"Voxel count: {voxel_count}")

# Helper functions
def viz_coords(stack, coord_array, pixel_value):
    z, x = coord_array.shape
    y = stack.shape[1]
    label_stack = np.zeros((z, y, x), dtype=np.uint8)
    z_idx, x_idx = np.meshgrid(np.arange(z), np.arange(x), indexing='ij')
    y_idx = coord_array
    mask = (y_idx >= 0) & (y_idx < y)  # ensure indices are within bounds
    label_stack[z_idx[mask], y_idx[mask], x_idx[mask]] = pixel_value

    return label_stack