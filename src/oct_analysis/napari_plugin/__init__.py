"""
Assembly of napari plugin widgets into scrollable tabs.
"""

# Third-party imports
from oct_analysis.napari_plugin import widgets
from qtpy.QtWidgets import QTabWidget

# Local imports
from oct_analysis.toolkit import utils


def main():
    # I/O Tab
    io_widgets = [
        widgets.clear_layers,
        # load file
        # load many files
        # save settings
        # load settings
        # save file
        # save many files
        widgets.load_file,
        widgets.handle_input,
        widgets.save,
        widgets.load_settings,
        # widgets.apply_loaded_settings_single,
    ]
    scrolltab_io = utils.create_scrolltab(widget_list=io_widgets, name="Loading/Saving")

    # Pre-Processing Tab
    pre_widgets = [
        widgets.ignore_slices,
        widgets.median_filter,
        widgets.roi_filter_2D,
        widgets.locate_window,
        widgets.zero_out_window,
        widgets.locate_substratum,
        widgets.zero_out_substratum,
    ]
    scrolltab_pre = utils.create_scrolltab(
        widget_list=pre_widgets, name="Pre-Processing"
    )

    # Binarize Tab
    bin_widgets = [
        widgets.increase_contrast,
        widgets.auto_threshold,
        widgets.remove_outliers,
        widgets.confirm_binarization,
    ]
    scrolltab_bin = utils.create_scrolltab(widget_list=bin_widgets, name="Binarization")

    # Evaluate Tab
    eval_widgets = [
        widgets.count_voxels,
        # widgets.height_map,
        # widgets.Bmap,
        # widgets.SC,
        # widgets.BTplot
        # widgets.BV
        # widgets.export
    ]
    scrolltab_eval = utils.create_scrolltab(widget_list=eval_widgets, name="Evaluation")

    # Merge Tabs
    tabs = QTabWidget()
    tabs.addTab(scrolltab_io, "Loading/Saving")
    tabs.addTab(scrolltab_pre, "Pre-Processing")
    tabs.addTab(scrolltab_bin, "Binarization")
    tabs.addTab(scrolltab_eval, "Evaluation")

    return tabs
