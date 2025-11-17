"""
Assembly of napari plugin widgets into scrollable tabs.
"""

# Third-party imports
from qtpy.QtWidgets import QTabWidget, QScrollArea, QWidget, QVBoxLayout

# Local imports
from oct_analysis.napari_plugin import widgets


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
        widgets.save,
        widgets.export_settings,
        widgets.load_settings,
        # widgets.apply_loaded_settings_single,
    ]
    scrolltab_io = create_scrolltab(widget_list=io_widgets)

    # Pre-Processing Tab
    pre_widgets = [
        widgets.keep_slices,
        widgets.locate_window,
        widgets.mark_cutoff,
        widgets.zero_out_window,
        widgets.median_filter,
        widgets.roi_filter_2D,
        widgets.locate_substratum,
        widgets.zero_out_substratum,
        widgets.confirm_segmentation,
    ]
    scrolltab_pre = create_scrolltab(widget_list=pre_widgets)

    # Binarize Tab
    bin_widgets = [
        widgets.median_filter,
        widgets.increase_contrast,
        widgets.auto_threshold,
        widgets.remove_outliers,
        widgets.confirm_binarization,
    ]
    scrolltab_bin = create_scrolltab(widget_list=bin_widgets)

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
    scrolltab_eval = create_scrolltab(widget_list=eval_widgets)

    # Merge Tabs
    tabs = QTabWidget()
    tabs.addTab(scrolltab_io, "Loading/Saving")
    tabs.addTab(scrolltab_pre, "Pre-Processing")
    tabs.addTab(scrolltab_bin, "Binarization")
    tabs.addTab(scrolltab_eval, "Evaluation")

    return tabs


# Helper function
# Creates a scrollable tab containing the provided widgets for napari plugin GUI
def create_scrolltab(
    widget_list: list,
) -> QScrollArea:
    inner_widget = QWidget()
    inner_layout = QVBoxLayout(inner_widget)
    inner_layout.setSpacing(30)

    for w in widget_list:
        wrapper = QWidget()
        wrapper.setObjectName("wrapper")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(5, 5, 5, 5)
        wrapper_layout.addWidget(w.native)
        wrapper.setStyleSheet("""
            #wrapper {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
        """)
        inner_layout.addWidget(wrapper)

    inner_layout.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner_widget)
    scroll.setMinimumWidth(400)

    scrolltab = scroll

    return scrolltab
