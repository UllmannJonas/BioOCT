from magicgui import magicgui
import napari
from napari.utils.notifications import show_info
import numpy as np
from qtpy.QtWidgets import QFileDialog
from pathlib import Path

from oct_analysis.octools import processing_functions as ip

oct_metadata_global = {} # Global variable to store metadata

@magicgui(call_button="Show Instructions (1/4)")
def show_instructionsA():
    instructionsA = (
        "<b>OCT Labeling Workflow:</b><br><br>"

        "<b>1. Load & Normalize</b><br>"
        "• Click <i>Load OCT</i> to open a .oct file<br>"
        "• This creates a hidden raw layer and a normalized image layer<br><br>"

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
        "-> Internally, the coordinates are located using the 'roi_filtered' layer<br>"
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
        "• Use <i>Save stack+mask_stack</i> to export normalized & binary layers as .nii.gz files<br>"
        "• Use <i>Save Settings</i> to export a JSON file of the current settings of all user-set values"
    )

    show_info(instructionsD)

@magicgui(call_button="Load OCT")
def load_oct(viewer: napari.Viewer):
    filepath, _ = QFileDialog.getOpenFileName(None, 'Select OCT file', '', 'OCT files (*.oct)') # type: ignore
    if not filepath:
        show_info("No file selected.")
        return # Abbrechen
    
    stack, metadata = ip.load_oct(Path(filepath)) # type: ignore
    oct_metadata_global = metadata # Store metadata globally

    viewer.add_image(stack, name=metadata['filename'], visible=False)
    
    stack_norm = (stack - stack.min()) / (stack.max() - stack.min())
    norm_layer = viewer.add_image(stack_norm, name='normalized', visible=True)
    norm_layer.metadata['oct_metadata'] = metadata # type: ignore

    show_info(f"Loaded {metadata['filename']}")

@magicgui(
            call_button="Apply Median Filter",
            filter_size={"widget_type": "SpinBox", "min": 1, "max": 101, "step": 2, "value": 3}
    )
def median_filter(filter_size, viewer: napari.Viewer):
    if 'normalized' not in viewer.layers:
        show_info("OCT File has to be loaded.")
        return
    
    stack = viewer.layers['normalized'].data

    median_filtered = ip.median_blur(stack, filter_size)

    if 'median_filtered' in viewer.layers:
        viewer.layers['median_filtered'].data = median_filtered
    else:
        viewer.add_image(median_filtered, name="median_filtered", visible=False)

@magicgui(call_button="Apply ROI 2D Filter",
            roi_size={"widget_type": "SpinBox", "min": 1, "max": 51, "step": 2, "value": 5}
)
def roi_filter_2D(roi_size, viewer: napari.Viewer):
    if 'median_filtered' not in viewer.layers:
        show_info("Median filter has to be applied first.")
        return
    
    stack = viewer.layers['median_filtered'].data

    roi_filtered = ip.roi_filter_2D(stack, roi_size)

    if 'roi_filtered' in viewer.layers:
        viewer.layers['roi_filtered'].data = roi_filtered
    else:
        viewer.add_image(roi_filtered, name="roi_filtered", visible=False)

@magicgui(call_button="Locate Window",
            ymin={"widget_type": "SpinBox", "min": 0, "max": oct_metadata_global.get('size_px', {}).get('y', 1000), "step": 1, "value": 0},
            ymax={"widget_type": "SpinBox", "min": 0, "max": oct_metadata_global.get('size_px', {}).get('y', 1000)+1, "step": 1, "value": 100},
            y_offset={"widget_type": "SpinBox", "min": -100, "max": 100, "step": 1, "value": 0}
)
def locate_window(ymin, ymax, y_offset, viewer: napari.Viewer):
    if 'roi_filtered' not in viewer.layers:
        show_info("ROI filter has to be applied first.")
        return
    stack = viewer.layers['roi_filtered'].data
    stack_norm = viewer.layers['normalized'].data

    window_coords = ip.locate_window(stack, ymin, ymax, y_offset)
    label_stack = viz_coords(stack_norm, window_coords, pixel_value=1)

    if 'window_coords' in viewer.layers:
        layer = viewer.layers['window_coords']
        layer.data = label_stack
    else:
        layer = viewer.add_labels(label_stack, name='window_coords', visible=True)
    
    layer.metadata['window_coords'] = window_coords

@magicgui(call_button="Zero Out Window")
def zero_out_window(viewer: napari.Viewer):
    if 'window_coords' not in viewer.layers:
        show_info("Window has to be located first.")
        return
    window_coords = viewer.layers['window_coords'].metadata.get('window_coords')
    stack_norm = viewer.layers['median_filtered'].data

    no_window = ip.zero_out_window(stack_norm, window_coords) # type: ignore

    if 'no_window' in viewer.layers:
        viewer.layers['no_window'].data = no_window
    else:
        viewer.add_image(no_window, name="no_window", visible=True)

@magicgui(call_button="Locate Substratum",
            ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 200},
            ymax={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 1000},
            y_offset={"widget_type": "SpinBox", "min": -100, "max": 100, "step": 1, "value": 0}
)
def locate_substratum(ymin, ymax, y_offset, viewer: napari.Viewer):
    if 'roi_filtered' not in viewer.layers:
        show_info("ROI filter has to be applied first.")
        return
    stack = viewer.layers['roi_filtered'].data
    stack_norm = viewer.layers['normalized'].data

    substratum_coords = ip.locate_substratum(stack, ymin, ymax, y_offset)
    label_stack = viz_coords(stack_norm, substratum_coords, pixel_value=2)

    if 'substratum_coords' in viewer.layers:
        layer = viewer.layers['substratum_coords']
        layer.data = label_stack
    else:
        layer = viewer.add_labels(label_stack, name="substratum_coords", visible=True)
    
    layer.metadata['substratum_coords'] = substratum_coords

@magicgui(call_button="Zero Out Substratum")
def zero_out_substratum(viewer: napari.Viewer):
    if 'substratum_coords' not in viewer.layers:
        show_info("Substratum must be located first.")
        return
    substratum_coords = viewer.layers['substratum_coords'].metadata.get('substratum_coords')
    stack_norm = (
        viewer.layers['no_window'].data if 'no_window' in viewer.layers
        else viewer.layers['median_filtered'].data
    )

    no_substratum = ip.zero_out_substratum(stack_norm, substratum_coords) # type: ignore

    if 'no_substratum' in viewer.layers:
        viewer.layers['no_substratum'].data = no_substratum
    else:
        layer = viewer.add_image(no_substratum, name="no_substratum", visible=True)

@magicgui(call_button="Increase contrast",
    percentile={"widget_type": "FloatSpinBox", "min": 0.0, "max": 100.0, "step": 0.5, "value": 1.0},
)
def increase_contrast(percentile, viewer: napari.Viewer):
    if 'no_substratum' not in viewer.layers:
        show_info("Substratum must be zeroed out first.")
        return

    stack = viewer.layers['no_substratum'].data
    
    contrast_enhanced = ip.increase_contrast(stack, percentile)
    ip.plot_histograms(stack, contrast_enhanced, percentile)

    if 'contrast_enhanced' in viewer.layers:
        viewer.layers['contrast_enhanced'].data = contrast_enhanced
    else:
        viewer.add_image(contrast_enhanced, name='contrast_enhanced', colormap='grey', gamma=1.0, visible=True)

    for lay in viewer.layers:
        lay.visible = False
    viewer.layers['contrast_enhanced'].visible = True

@magicgui(
    threshold={'widget_type': 'FloatSpinBox', 'min': 0.0, 'max': 1.0, 'step': 0.001, 'value': 0.7},
    auto_call=True
)
def binarize(threshold, viewer: napari.Viewer):
    if 'contrast_enhanced' not in viewer.layers:
        show_info("Substratum must be zeroed out first.")
        return
    
    stack = viewer.layers['contrast_enhanced'].data

    # finetuning threshold toggle nur auf aktuellem slice
    binary = (stack > threshold).astype(np.uint8)

    if 'binary' in viewer.layers:
        viewer.layers['binary'].data = binary
    else:
        viewer.add_labels(binary, name="binary", visible=True)

@magicgui(
        outlier_size={'widget_type': 'SpinBox', 'min': 0, 'max': 100, 'step': 1, 'value': 2},
        auto_call=True
)
def remove_outliers(outlier_size, viewer: napari.Viewer):
    stack = viewer.layers['binary'].data

    cleaned_binary = ip.rm_outliers(stack, outlier_size)

    viewer.layers['binary'].data = cleaned_binary

@magicgui(
        call_button='Save stack+mask_stack',
        output_directory={"widget_type": "FileEdit", "mode": "d", "value": str(Path.home())}
)
def save(output_directory, viewer: napari.Viewer):
    stack = viewer.layers['normalized'].data
    binary_stack = viewer.layers['binary'].data
    metadata = viewer.layers['normalized'].metadata.get('oct_metadata')

    if ip.save(stack, metadata, binary_stack, output_directory): # type: ignore
        viewer.layers.clear()
        show_info(f"Saved stack and binary mask to {output_directory}")


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
