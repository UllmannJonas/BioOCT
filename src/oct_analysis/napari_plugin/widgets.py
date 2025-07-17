from magicgui import magicgui
import napari
from napari.utils.notifications import show_info
import numpy as np
from qtpy.QtWidgets import QFileDialog
from pathlib import Path

from oct_analysis.octools import processing_functions as ip

@magicgui(call_button="Show Instructions (1/4)")
def show_instructionsA():
    instructionsA = (
        "<b>OCT Labeling Workflow:</b><br><br>"

        "<b>1. Load & Normalize</b><br>"
        "• Click <i>Load OCT</i> to open a .oct file<br>"
        "• This creates a hidden raw layer and a target (normalized) image layer<br><br>"

        "<b>2. Preprocessing</b><br>"
        "• Apply <i>Median Filter</i> to smoothen noise but preserve edges<br>"
        "• Apply <i>ROI 2D Filter</i> to enhance detection of horizontal edges<br><br>"
    )

    show_info(instructionsA)

@magicgui(call_button="Show Instructions (2/4)")
def show_instructionsB():
    instructionsB = (
        "<b>3. Window/Substratum Detection</b><br>"
        "• Use <i>Locate Window</i> to find window coordinates<br>"
        "• Click <i>Zero Out Window</i> to mask it<br>"
        "• Use <i>Locate Substratum</i> to detect the substratum<br>"
        "• Click <i>Zero Out Substratum</i> to mask it<br>"
        "-> Internally, the coordinates are located using the 'edge_enhanced' layer<br>"
        "-> The masking is then applied to the median_filtered layer (important for binarization later)"
    )

    show_info(instructionsB)

@magicgui(call_button="Show Instructions (3/4)")
def show_instructionsC():
    instructionsC = (
        "<b>4. Postprocessing</b><br>"
        "• Use <i>Increase Contrast</i> to improve binarization accuracy<br>"
        "• Adjust <i>Threshold</i> to binarize. Changing the value auto-calls the binarize-function<br>"
        "-> The threshold is calculated on the masked median_filtered layer (no_substratum). Zero-values are ignored<br>"
        "• Optionally use <i>Remove Outliers</i> to clean up biofilm signal in the background noise (also auto-called)<br><br>"
    )

    show_info(instructionsC)

@magicgui(call_button="Show Instructions (4/4)")
def show_instructionsD():
    instructionsD = (
        "<b>5. Save</b><br>"
        "• Use <i>Save stack+mask_stack</i> to export original & binary layers as .nii.gz files<br>"
        "• Use <i>Save Settings</i> to export a JSON file of the current settings of all user-set values"
    )

    show_info(instructionsD)


@magicgui(call_button="Load OCT")
def load_oct(viewer: napari.Viewer):
    filepath, _ = QFileDialog.getOpenFileName(None, 'Select OCT file', '', 'OCT files (*.oct *.nii *.nii.gz)') # type: ignore
    if not filepath:
        show_info("No file selected.")
        return # Abbrechen
    
    stack, metadata = ip.load_oct(Path(filepath)) # type: ignore

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
        layer = viewer.layers['window_coords']
        layer.data = label_stack
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
    reference_stack = viewer.layers['target'].data

    substratum_coords = ip.locate_substratum(working_stack, ymin, ymax, y_offset)
    label_stack = viz_coords(reference_stack, substratum_coords, pixel_value=2)

    if 'substratum_coords' in viewer.layers:
        layer = viewer.layers['substratum_coords']
        layer.data = label_stack
    else:
        coords_layer = viewer.add_labels(label_stack, name="substratum_coords", visible=True)
    
    coords_layer.metadata['substratum_coords'] = substratum_coords

@magicgui(call_button="Zero Out Substratum")
def zero_out_substratum(viewer: napari.Viewer):
    if 'target' not in viewer.layers:
        show_info("Create target layer first.")
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
    percentile={"widget_type": "FloatSpinBox", "min": 0.0, "max": 100.0, "step": 0.5, "value": 1.0},
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

    viewer.layers['target'].data = contrast_enhanced

    for lay in viewer.layers:
        lay.visible = False
    viewer.layers['target'].visible = True

@magicgui(
    threshold={'widget_type': 'FloatSpinBox', 'min': 0.0, 'max': 1.0, 'step': 0.001, 'value': 0.7},
    auto_call=True
)
def binarize(threshold, viewer: napari.Viewer):
    if 'target' not in viewer.layers:
        show_info("Create target layer first.")
        return

    stack = viewer.layers['target'].data

    # TODO: finetuning threshold toggle nur auf aktuellem slice
    binary = (stack > threshold).astype(np.uint8)

    if 'binary' in viewer.layers:
        viewer.layers['binary'].data = binary
    else:
        viewer.add_labels(binary, name="binary", visible=True)
    
    if 'target' in viewer.layers:
        target_layer = viewer.layers['target']
        viewer.layers.remove(target_layer)

@magicgui(
        outlier_size={'widget_type': 'SpinBox', 'min': 0, 'max': 100, 'step': 1, 'value': 2},
        auto_call=True
)
def remove_outliers(outlier_size, viewer: napari.Viewer):
    stack = viewer.layers['binary'].data

    cleaned_binary = ip.rm_outliers(stack, outlier_size)

    viewer.layers['binary'].data = cleaned_binary

@magicgui(
        call_button='Save Original & Binary',
        output_directory={"widget_type": "FileEdit", "mode": "d", "value": str(Path.home())}
)
def save(output_directory, viewer: napari.Viewer):
    original_layer = next((layer for layer in viewer.layers if "Original" in layer.name), None)
    if original_layer is not None:
        original_stack = original_layer.data
        metadata = original_layer.metadata.get('oct_metadata')
    else:
        show_info("Original layer not found. Please load an OCT file first.")
        return
    binary_stack = viewer.layers['binary'].data

    if ip.save(original_stack, metadata, binary_stack, output_directory): # type: ignore
        viewer.layers.clear()
        show_info(f"Saved stack and binary mask to {output_directory}")

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
