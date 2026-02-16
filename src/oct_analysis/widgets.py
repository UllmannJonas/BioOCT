"""
Frontend widget code for napari plugin.
The backend functions (oct_analysis.toolkit) are called here with magicgui and error handling decorators.
Magicgui-decorator turns functions into GUI widgets automatically.
Error handling decorator shows error messages (upon exception in backend) in a popup window instead of crashing napari.
The widgets are then assembled into scrollable tabs in __init__.py.
"""

# region imports
# Python native imports
from pathlib import Path

# Third party imports
from magicgui import magicgui
import napari
from napari.utils.notifications import show_info, show_warning
import numpy as np
from qtpy.QtWidgets import QFileDialog


# Local imports
import bio_oct
from bio_oct import pipeline

from ._plugin_utils import (
    SessionState,
    gui_error_handler,
    update_layer,
    vizualize_coords,
    layer_exists_check,
    create_threshold_widget,
)
# endregion imports


state = SessionState()


# region I/O
# -------------------------------------------------------------
# -------------------- Widgets for I/O tab --------------------
@magicgui(call_button="Load OCT File")
@gui_error_handler
def load_file(viewer: napari.Viewer):
    if not state.reset_flag:
        show_warning('Reset Session first by executing "Clear Layers"')
        return

    filepath, _ = QFileDialog.getOpenFileName(
        None,
        "Select file",
        str(Path.home()),
        "Format (*.oct)",
    )
    if not filepath:
        show_info("No file selected.")
        return

    oct_ = bio_oct.ThorlabsOCT(filepath)

    state.reset_flag = False
    state.source_dir = Path(filepath).parent
    state.filename = Path(filepath).stem
    state.affine = oct_.affine
    state.spacing = oct_.spacing

    update_layer(viewer, oct_.stack, oct_.affine, name=state.filename)

    update_widget_presets(oct_.stack.shape[1] - 1)

    show_info(f"Loaded {state.filename} successfully.")


@magicgui(call_button="Clear Layers and Reset Session")
def clear_layers(viewer: napari.Viewer):
    viewer.layers.clear()
    state.reset()
    show_info("Ready for new Session!")


@magicgui(call_button='Create "working copy"-Layer')
@gui_error_handler
def make_working_copy(viewer: napari.Viewer):
    layer = layer_exists_check(viewer, state.filename)
    stack = np.copy(layer.data)
    update_layer(viewer, stack, affine=state.affine, name="working copy")


@magicgui(call_button="Export Current Pipeline",
    user_handle={
        "label": "User",
        "value": "user_name"
    },
    output_directory={
        "widget_type": "FileEdit",
        "label": "Save to:",
        "mode": "d",
        "value": str(state.source_dir),
    })
@gui_error_handler
def export_pipeline(user_handle: str, output_directory: str):
    if user_handle == "user_name":
        show_warning("Please give a username/identifier")
        return
    yaml_savepath = Path(output_directory) / f"pipeline_{user_handle}_{state.filename}.yaml"
    state.pl.to_yaml(yaml_savepath)
    show_info(f"Exported Processing Steps to {yaml_savepath}")

# endregion I/O


# region pre-processing
# ------------------------------------------------------------------------
# -------------------- Widgets for pre-processing tab --------------------
@magicgui(
    call_button="Remove Window",
    ymin={"widget_type": "SpinBox", "min": 0, "step": 1, "value": 0},
    ymax={"widget_type": "SpinBox", "min": 0, "step": 1, "value": 100},
    y_offset={"widget_type": "SpinBox", "min": -20, "max": 20, "step": 1, "value": 0},
)
@gui_error_handler
def remove_window(viewer: napari.Viewer, ymin, ymax, y_offset, preview: bool = True):
    stack = layer_exists_check(viewer, "working copy").data
    reference_stack = layer_exists_check(viewer, state.filename).data

    labelstack = vizualize_coords(
        reference_stack,
        bio_oct.locate_window(stack, ymin, ymax, y_offset)
    )

    coords_layer = update_layer(
        viewer,
        labelstack,
        affine=state.affine,
        type="labels",
        name="window_coords",
    )

    if not preview:
        state.window_coords = bio_oct.locate_window(stack, ymin, ymax, y_offset)

        """
        #* This WORKS! -> state can be saved in metadata!
        window_coords = bio_oct.locate_window(stack, ymin, ymax, y_offset)
        viewer.layers[state.filename].metadata["window_coords"] = window_coords
        """

        no_window = bio_oct.zero_out_window(stack, state.window_coords)
        state.pl.add_step(pipeline.pipe_remove_window, ymin=ymin, ymax=ymax, y_offset=y_offset)
        update_layer(viewer, no_window, state.affine, name="working copy")
        viewer.layers.remove(coords_layer)


"""
class RemoveWindow:
    def __init__(self, viewer: napari.Viewer):
        self.viewer = viewer
        self.axial_min: int = 0
        self.axial_max: int = 100
        self.bounds_layer = None

        self.define_area = magicgui(
            gui_error_handler(self._define_area),
            auto_call=True
        )

        self.remove_window = magicgui(
            gui_error_handler(self._remove_window),
            call_button="Remove Window",
            axial_offset={"widget_type": "SpinBox", "min": -20, "max": 20, "step": 1, "value": 0},
        )

    def _define_area(self, viewer: napari.Viewer, upper_bound: int, lower_bound: int):
        reference_layer = layer_exists_check(viewer, state.filename)
        upper_bound_surface = state.draw_flat_surface(upper_bound, reference_layer.data)
        lower_bound_surface = state.draw_flat_surface(lower_bound, reference_layer.data)
        bounds_combined = upper_bound_surface + lower_bound_surface
        self.bounds_layer = update_layer(
            viewer,
            data=bounds_combined,
            affine=state.affine,
            type="labels",
            name="search window area"
        )
        self.axial_min = upper_bound
        self.axial_max = lower_bound

    def _remove_window(self, viewer: napari.Viewer, axial_offset, preview: bool = True):
        if self.bounds_layer is None:
            raise ValueError
        stack = viewer.layers["working copy"].data
        reference_stack = viewer.layers[state.filename].data

        labelstack = vizualize_coords(
            stack=reference_stack,
            coord_array=bio_oct.locate_window(stack, self.axial_min, self.axial_max, axial_offset)
        )

        coords_layer = update_layer(
            viewer,
            labelstack,
            affine=state.affine,
            type="labels",
            name="window_coords",
        )

        if not preview:
            state.window_coords = bio_oct.locate_window(stack, self.axial_min, self.axial_max, axial_offset)
            no_window = bio_oct.zero_out_window(stack, state.window_coords)
            state.add_step(pipeline.pipe_remove_window, ymin=self.axial_min, ymax=self.axial_max, y_offset=axial_offset)
            update_layer(viewer, no_window, state.affine, name="working copy")

            viewer.layers.remove(coords_layer)
            viewer.layers.remove(self.bounds_layer)
"""


@magicgui(
    call_button="Remove Substratum (Intensity-Based)",
    ymin={"widget_type": "SpinBox", "min": 0, "step": 1, "value": 0, "label": "Upper Bound"},
    ymax={"widget_type": "SpinBox", "min": 0, "step": 1, "value": 100, "label": "Lower Bound"},
    offset={"widget_type": "SpinBox", "min": -20, "max": 20, "step": 1, "value": 0},
    clean_substratum={"value": False},
    outlier_size={
        "widget_type": "Slider",
        "min": 0,
        "max": 20,
        "step": 1,
        "value": 0,
        "label": "Outlier Size",
    },
)
@gui_error_handler
def remove_substratum_via_intensity(
    viewer: napari.Viewer,
    # search area
    ymin: int,
    ymax: int,
    # argmax param
    offset: int,
    # clean substratum params
    clean_substratum: bool,
    outlier_size: int,
    # preview y/n
    preview: bool = True
):
    reference_stack = layer_exists_check(viewer, state.filename).data
    stack = layer_exists_check(viewer, "working copy").data

    state.substratum_coords, state.substratum_coords_nan = bio_oct.locate_substratum(
        stack, ymin, ymax, offset
    )

    if clean_substratum:
        state.substratum_coords = bio_oct.clean_substratum_coords(
            state.substratum_coords_nan, reference_stack, outlier_size=outlier_size
        )
        state.substratum_coords_nan = None
        show_info("Success! No NaN values remaining!")

    labelstack = vizualize_coords(
        reference_stack, state.substratum_coords, state.substratum_coords_nan
    )

    coords_layer = update_layer(
        viewer,
        labelstack,
        state.affine,
        type="labels",
        name="substratum_coords",
    )

    if not preview:
        no_substratum = bio_oct.zero_out_substratum(stack, state.substratum_coords)

        update_layer(viewer, no_substratum, affine=state.affine, name="working copy")

        state.pl.add_step(pipeline.pipe_locate_substratum, ymin=ymin, ymax=ymax, y_offset=offset)
        if clean_substratum:
            state.pl.add_step(pipeline.pipe_clean_substratum_coords, outlier_size=outlier_size)
        state.pl.add_step(pipeline.pipe_zero_out_substratum)

        viewer.layers.remove(coords_layer)


"""
#!Experimental
@magicgui(
    call_button="Remove Substratum (TEST)",
    ymin={"widget_type": "SpinBox", "min": 0, "max": 1000, "step": 1, "value": 0, "label": "Upper Bound"},
    ymax={"widget_type": "SpinBox", "min": 0, "max": 1001, "step": 1, "value": 100, "label": "Lower Bound"},
    window_size={"widget_type": "SpinBox", "min": -20, "max": 20, "step": 1, "value": 0},
    outlier_size={
        "widget_type": "Slider",
        "min": 0,
        "max": 20,
        "step": 1,
        "value": 0,
        "label": "Outlier Size",
    },
)
@gui_error_handler
def remove_substratum_via_test(    viewer: napari.Viewer,
    # search area
    ymin: int,
    ymax: int,
    # argmax param
    window_size: int,
    # clean substratum params
    clean_substratum: bool,
    outlier_size: int,
    # preview y/n
    preview: bool = True
):
    reference_layer = layer_exists_check(viewer, state._filename)
    copy_layer = layer_exists_check(viewer, "working copy")

    stack = copy_layer.data
    reference_stack = reference_layer.data

    state._substratum_coords, state._substratum_coords_nan = bio_oct.locate_substratum(
        stack, ymin, ymax
    )


    #! Experimental 1D gradient search in window "above" argmax
    b_scans, _, lateral = stack.shape
    edge = np.empty_like(state._substratum_coords)

    for bscan in range(b_scans):
        for ascan in range(lateral):
            y0 = state._substratum_coords[bscan, ascan]

            y_start = max(1, y0 - window_size)  # 10 px window
            window = stack[bscan, y_start:y0+1, ascan]
            window_smoothed = gaussian_filter1d(window, sigma=1.0)

            # gradient (dy)
            g = np.diff(window_smoothed)

            # most negative slope → strongest drop
            local_idx = np.argmin(g)

            # map back to global y
            edge[bscan, ascan] = y_start + local_idx
    state._substratum_coords = edge
    #!end Experimental part


    if clean_substratum:
        state._substratum_coords = bio_oct.clean_substratum_coords(
            state._substratum_coords_nan, reference_stack, outlier_size=outlier_size
        )
        state._substratum_coords_nan = None
        show_info("Success! No NaN values remaining!")

    labelstack = vizualize_coords(
        reference_stack, state._substratum_coords, state._substratum_coords_nan
    )

    update_layer(
        viewer,
        labelstack,
        reference_layer.affine,
        type="labels",
        name="substratum_coords",
    )

    if not preview:
        no_substratum = bio_oct.zero_out_substratum(stack, state._substratum_coords)

        update_layer(viewer, no_substratum, affine=state._affine, name="working copy")

        state.add_step(pipeline.pipe_locate_substratum, ymin=ymin, ymax=ymax, y_offset=offset)
        if clean_substratum:
            state.add_step(pipeline.pipe_clean_substratum_coords, outlier_size=outlier_size)
        state.add_step(pipeline.pipe_zero_out_substratum)

        coords_layer = viewer.layers["substratum_coords"]
        viewer.layers.remove(coords_layer)
"""


@magicgui(
    call_button="Remove Substratum (Gradient-Based)",
    ymin={"widget_type": "SpinBox", "min": 0, "step": 1, "value": 0, "label": "Upper Bound"},
    ymax={"widget_type": "SpinBox", "min": 0, "step": 1, "value": 100, "label": "Lower Bound"},
    sigma={
        "widget_type": "FloatSpinBox",
        "min": 0.0,
        "max": 3.0,
        "step": 0.1,
        "value": 0,
        "label": "Gaussian Blur Sigma",
    },
    lower_threshold={
        "widget_type": "FloatSpinBox",
        "min": 0.0,
        "max": 0.1,
        "step": 0.005,
        "value": 0.0,
        "label": "Weak Edge Threshold",
    },
    upper_threshold={
        "widget_type": "FloatSpinBox",
        "min": 0.0,
        "max": 0.1,
        "step": 0.005,
        "value": 0.0,
        "label": "Strong Edge Threshold",
    },
    clean_substratum={"value": False},
    outlier_size={
        "widget_type": "SpinBox",
        "min": 0,
        "max": 20,
        "step": 1,
        "value": 0,
        "label": "Outlier Size",
    },
)
@gui_error_handler
def remove_substratum_via_canny(
    viewer: napari.Viewer,
    # search area
    ymin: int,
    ymax: int,
    # canny params
    sigma: float,
    lower_threshold: float,
    upper_threshold: float,
    # clean substratum params
    clean_substratum: bool,
    outlier_size: int,
    # preview y/n
    preview: bool = True
):
    reference_stack = layer_exists_check(viewer, state.filename).data
    stack = layer_exists_check(viewer, "working copy").data


    # canny edge detection
    canny_edges = bio_oct.canny_edge_filter(
        reference_stack,
        ymin,
        ymax,
        sigma,
        lower_threshold,
        upper_threshold,
    )
    canny_layer = update_layer(viewer, canny_edges, affine=state.affine, name="canny edges")

    # locating the canny edge as substratum
    state.substratum_coords, state.substratum_coords_nan = bio_oct.locate_substratum(
        canny_edges, ymin, ymax
    )

    if clean_substratum:
        state.substratum_coords = bio_oct.clean_substratum_coords(
            state.substratum_coords_nan, reference_stack, outlier_size=outlier_size
        )
        state.substratum_coords_nan = None
        show_info("Success! No NaN values remaining!")

    labelstack = vizualize_coords(
        reference_stack, state.substratum_coords, state.substratum_coords_nan
    )

    coords_layer = update_layer(
        viewer,
        labelstack,
        state.affine,
        type="labels",
        name="substratum_coords",
    )

    if not preview:
        no_substratum = bio_oct.zero_out_substratum(stack, state.substratum_coords)

        update_layer(viewer, no_substratum, affine=state.affine, name="working copy")

        state.pl.add_step(pipeline.pipe_canny_edge_filter, ymin=ymin, ymax=ymax, sigma=sigma, lower_threshold=lower_threshold, upper_threshold=upper_threshold)
        state.pl.add_step(pipeline.pipe_locate_substratum, ymin=ymin, ymax=ymax)
        if clean_substratum:
            state.pl.add_step(pipeline.pipe_clean_substratum_coords, outlier_size=outlier_size)
        state.pl.add_step(pipeline.pipe_zero_out_substratum)

        viewer.layers.remove(coords_layer)
        viewer.layers.remove(canny_layer)


@magicgui(call_button="Confirm Segmentation")
@gui_error_handler
def confirm_segmentation(viewer: napari.Viewer):
    reference_stack = layer_exists_check(viewer, state.filename).data
    state.create_valid_mask(reference_stack)

    confirmed = np.zeros_like(reference_stack)
    confirmed[state.valid_mask] = reference_stack[state.valid_mask]

    state.pl.add_step(pipeline.pipe_confirm_segmentation)

    update_layer(viewer, confirmed, affine=state.affine, name="working copy")


# endregion pre-processing


# region binarization
# ----------------------------------------------------------------------
# -------------------- Widgets for binarization tab --------------------
@magicgui(
    call_button="Increase Contrast",
    percentile={
        "widget_type": "FloatSlider",
        "label": "Percentile",
        "min": 0.0,
        "max": 5.0,
        "value": 0.0,
    },
)
@gui_error_handler
def increase_contrast(viewer: napari.Viewer, percentile: float, preview: bool = True):
    stack = layer_exists_check(viewer, "working copy").data

    contrast_enhanced = bio_oct.increase_contrast(stack, state.valid_mask, percentile)
    if preview:
        preview_layer = update_layer(viewer, contrast_enhanced, affine=state.affine, name="contrast-preview")
    else:
        try:
            preview_layer = layer_exists_check(viewer, "contrast-preview")
            viewer.layers.remove(preview_layer)
        except ValueError:
            pass
        update_layer(viewer, contrast_enhanced, affine=state.affine, name="working copy")
        state.pl.add_step(pipeline.pipe_increase_contrast, percentile=percentile)


@magicgui(
    call_button="Apply Gaussian Blur",
    sigma={
        "widget_type": "FloatSlider",
        "min": 0.0,
        "max": 3.0,
        "step": 0.1,
        "value": 0.0,
        "label": "Sigma",
    },
)
@gui_error_handler
def gauss_filter(viewer: napari.Viewer, sigma: float, preview: bool = True):
    stack = layer_exists_check(viewer, "working copy").data

    gauss_filtered = bio_oct.horizontal_gaussian_filter(stack, state.valid_mask, sigma)
    if preview:
        update_layer(viewer, gauss_filtered, affine=state.affine, name="gauss_blur-preview")
    else:
        try:
            preview_layer = layer_exists_check(viewer, "gauss_blur-preview")
            viewer.layers.remove(preview_layer)
        except ValueError:
            pass
        update_layer(viewer, gauss_filtered, affine=state.affine, name="working copy")
        state.pl.add_step(pipeline.pipe_horizontal_gauss_filter, sigma=sigma)


@magicgui(call_button="Calculate Thresholds")
@gui_error_handler
def auto_threshold(viewer: napari.Viewer):
    stack = layer_exists_check(viewer, "working copy").data

    thresholds = bio_oct.get_thresholds(stack, state.valid_mask)
    bio_oct.plot_thresholds(stack, thresholds, state.valid_mask)

    # state.thresh_method is set inside create_threshold_widget() when user selects method
    widget = create_threshold_widget(viewer, thresholds, stack, state)
    viewer.window.add_dock_widget(widget, name="Select Thresholding Method")


@magicgui(
    call_button="Remove Outliers",
    outlier_size={
        "widget_type": "Slider",
        "min": 0,
        "max": 20,
        "step": 1,
        "value": 0,
        "label": "Outlier Size",
    },
)
@gui_error_handler
def remove_outliers(viewer: napari.Viewer, outlier_size: int, preview: bool = True):
    stack = layer_exists_check(viewer, "binary").data

    outliers_removed = bio_oct.remove_outliers(stack.astype(bool), outlier_size, out="uint8")
    if preview:
        update_layer(viewer, outliers_removed, affine=state.affine, type="labels", name="rm_outliers-preview")
    else:
        try:
            preview_layer = layer_exists_check(viewer, "rm_outliers-preview")
            viewer.layers.remove(preview_layer)
        except ValueError:
            pass
        update_layer(viewer, outliers_removed, affine=state.affine, type="labels", name="binary")


@magicgui(call_button="Confirm Binarization")
@gui_error_handler
def confirm_binarization(viewer: napari.Viewer):
    _ = layer_exists_check(viewer, "binary")

    if state.thresh_method != "none":
        state.pl.add_step(pipeline.pipe_apply_threshold, threshold_method=state.thresh_method)
    if remove_outliers.outlier_size.value != 0:
        state.pl.add_step(pipeline.pipe_remove_outliers, outlier_size=remove_outliers.outlier_size.value)

    for lay in list(viewer.layers):
        if lay.name not in ["binary", state.filename]:
            viewer.layers.remove(lay)


# endregion binarization


# region evaluation
# --------------------------------------------------------------------
# -------------------- Widgets for evaluation tab --------------------
@magicgui(
    call_button="Generate Height Map",
    measure={"value": False},
    max_height_µm={
        "widget_type": "SpinBox",
        "label": "Max. Height [µm]",
    },
    output_directory={
        "widget_type": "FileEdit",
        "label": "Save to:",
        "mode": "d",
        "value": str(Path.home()),
    },
    confirm_height={"value": False},
    auto_call=True
)
@gui_error_handler
def make_height_map(
    viewer: napari.Viewer,
    measure: bool,
    max_height_µm: int,
    output_directory: str,
    confirm_height: bool
):
    if not measure:
        return
    reference_layer = layer_exists_check(viewer, state.filename)
    binary_layer = layer_exists_check(viewer, "binary")

    b_scans, axial, lateral = reference_layer.data.shape
    assert state.spacing is not None
    y_coordinate = min(int(max_height_µm / (state.spacing.axial * 1000)), axial - 1)

    update_layer(
        viewer,
        vizualize_coords(
            stack=reference_layer.data,
            coord_array=np.full((b_scans, lateral), y_coordinate, dtype=int)),
        affine=state.affine,
        type="labels",
        name="max_height_HM"
    )

    if confirm_height:
        helper_layer = layer_exists_check(viewer, "max_height_HM")
        viewer.layers.remove(helper_layer)
        
        savepath = Path(output_directory) / f"{state.filename}_HM.png"
        bio_oct.save_height_map(
            binary_stack=binary_layer.data,
            height_map=bio_oct.calc_height_map(
                binary_layer.data, state.spacing, state.substratum_coords
            ),
            spacing=state.spacing,
            max_height_px=y_coordinate,
            savepath=savepath,
        )
        show_info(f"Saved Height Map to {savepath}")


@magicgui(
    call_button="Generate Biovolume Map",
    output_directory={
        "widget_type": "FileEdit",
        "label": "Save to:",
        "mode": "d",
        "value": str(Path.home()),
    },
)
@gui_error_handler
def make_b_map(
    viewer: napari.Viewer,
    output_directory: str
):
    binary_layer = layer_exists_check(viewer, "binary")

    assert state.spacing is not None
    savepath = Path(output_directory) / f"{state.filename}_BM.png"
    bio_oct.save_b_map(
        binary_stack=binary_layer.data,
        b_map=bio_oct.calc_b_map(binary_layer.data, state.spacing),
        spacing=state.spacing,
        savepath=savepath
    )
    show_info(f"Saved B-Map to {savepath}")


@magicgui(
    call_button="Export Metrics to CSV",
    min_height_SC={
        "widget_type": "SpinBox",
        "label": "Min. Height SC [µm]",
    },
    output_directory={
        "widget_type": "FileEdit",
        "label": "Save to:",
        "mode": "d",
        "value": str(Path.home()),
    },
)
@gui_error_handler
def calc_save_metrics(viewer: napari.Viewer, min_height_SC: int, output_directory: str):
    binary_stack = layer_exists_check(viewer, "binary").data

    assert state.spacing is not None
    min_cover = max(int(min_height_SC / (state.spacing.axial * 1000)), 0)

    _, axial, _ = layer_exists_check(viewer, state.filename).data.shape
    max_HM_px = min(int(make_height_map.max_height_µm.value / (state.spacing.axial * 1000)), axial - 1)
    state.pl.add_evaluation_step(
        max_HM_μm=make_height_map.max_height_µm.value,
        max_HM_px=max_HM_px,
        min_SC_μm=min_height_SC,
        min_SC_px=min_cover
    )

    savepath = Path(output_directory) / f"{state.filename}_metrics.csv"
    bio_oct.metrics_to_csv(
        metrics=bio_oct.calc_biofilm_metrics(
            binary_stack, state.spacing, state.substratum_coords, min_cover, state.filename
        ),
        savepath=savepath
    )

    show_info(f"Exported metrics to {savepath}")


# endregion evaluation


# region batch processing
# ---------------------------------------------------------------
# -------------------- Widgets for batch tab --------------------
@magicgui(
    call_button="Load OCT Timeseries",
    source={"choices": ["from OCT folder", "from zarr file"], "label": "Source"},
)
@gui_error_handler
def load_timeseries(viewer: napari.Viewer, source="from OCT folder"):
    match source:
        case "from zarr file":
            folderpath = QFileDialog.getExistingDirectory(
                None, "Select zarr folder", str(state.source_dir)
            )
            if not folderpath:
                show_info("No zarr folder selected.")
                return
            zarr_path = state.pl.set_data_source(Path(folderpath))
            zarr_stack = bio_oct.load_zarr(zarr_path)
            dask_stack = bio_oct.zarr_to_dask(zarr_stack)
            viewer.add_image(dask_stack, name="timeseries", contrast_limits=[0, 1])

        case "from OCT folder":
            folderpath = QFileDialog.getExistingDirectory(
                None, "Select folder containing OCT timeseries", str(state.source_dir)
            )
            if not folderpath:
                show_info("No folder selected.")
                return
            zarr_path = state.pl.set_data_source(Path(folderpath))
            zarr_stack = bio_oct.load_zarr(zarr_path)
            dask_stack = bio_oct.zarr_to_dask(zarr_stack)
            viewer.add_image(dask_stack, name="timeseries", contrast_limits=[0, 1])


@magicgui(call_button="Load Pipeline")
@gui_error_handler
def load_pipeline(viewer: napari.Viewer):
    pipeline_file, _ = QFileDialog.getOpenFileName(
        None,
        "Select settings file",
        str(state.source_dir),
        "Format (*.yaml)",
    )
    if not pipeline_file:
        show_info("No file selected.")
        return

    state.pl.load_pipeline(Path(pipeline_file))
    show_info(f"Loaded {Path(pipeline_file).name}")


@magicgui(call_button="Process Batch")
@gui_error_handler
def process_batch():
    state.pl.execute()


# endregion batch processing


# region helper-functions
# _________________________________________________
# -------------------- Helpers --------------------
# NEED MANUAL UPDATES

## Update all widget presets with values from loaded stack
def update_widget_presets(axial_max_idx: int) -> None:
    assert state.spacing is not None

    export_pipeline.output_directory.value = str(state.source_dir)
    make_height_map.output_directory.value = str(state.source_dir)
    make_b_map.output_directory.value = str(state.source_dir)
    calc_save_metrics.output_directory.value = str(state.source_dir)

    remove_window.ymin.max = axial_max_idx
    remove_window.ymax.max = axial_max_idx

    remove_substratum_via_intensity.ymin.max = axial_max_idx
    remove_substratum_via_intensity.ymax.max = axial_max_idx

    remove_substratum_via_canny.ymin.max = axial_max_idx
    remove_substratum_via_canny.ymax.max = axial_max_idx

    # +1 because of indexing: [5, 5, 5] -> max_idx is 2 (counting from 0), while array-length is 3
    make_height_map.max_height_µm.max = (axial_max_idx + 1) * state.spacing.axial
    calc_save_metrics.min_height_SC.max = ((axial_max_idx + 1) * state.spacing.axial * 1000) * 0.1


# endregion helper-functions
