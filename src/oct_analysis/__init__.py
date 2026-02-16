"""
Assembly of napari plugin widgets into scrollable tabs.
"""

from typing import Union, Any

# Third-party imports
from qtpy.QtWidgets import QTabWidget, QScrollArea, QWidget, QVBoxLayout

# Local imports
from oct_analysis import widgets


def main():
    # I/O Tab
    io_widgets = [
        widgets.load_file,
        widgets.clear_layers,
        widgets.make_working_copy,
        widgets.export_pipeline,
    ]
    scrolltab_io = create_scrolltab(widget_list=io_widgets)

    # Pre-Processing Tab
    pre_widgets = [
        widgets.remove_window,
        widgets.remove_substratum_via_intensity,
        widgets.remove_substratum_via_canny,
        widgets.confirm_segmentation,
    ]
    scrolltab_pre = create_scrolltab(widget_list=pre_widgets)

    # Binarize Tab
    bin_widgets = [
        widgets.increase_contrast,
        widgets.gauss_filter,
        widgets.auto_threshold,
        widgets.remove_outliers,
        widgets.confirm_binarization,
    ]
    scrolltab_bin = create_scrolltab(widget_list=bin_widgets)

    # Evaluate Tab
    eval_widgets = [
        widgets.make_height_map,
        widgets.make_b_map,
        widgets.calc_save_metrics,
    ]
    scrolltab_eval = create_scrolltab(widget_list=eval_widgets)

    # Batch Tab
    batch_widgets = [
        widgets.load_timeseries,
        widgets.load_pipeline,
        widgets.process_batch,
    ]
    scrolltab_batch = create_scrolltab(widget_list=batch_widgets)

    # Merge Tabs
    tabs = QTabWidget()
    tabs.addTab(scrolltab_io, "I/O")
    tabs.addTab(scrolltab_pre, "Segmentation")
    tabs.addTab(scrolltab_bin, "Binarization")
    tabs.addTab(scrolltab_eval, "Evaluation")
    tabs.addTab(scrolltab_batch, "Batch Processing")

    return tabs


# Helper function
# Creates a scrollable tab containing the provided widgets for napari plugin GUI
def create_scrolltab(
    widget_list: list[Union[dict[str, str], Any]],
) -> QScrollArea:
    inner_widget = QWidget()
    inner_layout = QVBoxLayout(inner_widget)
    inner_layout.setSpacing(30)

    for w in widget_list:
        wrapper = QWidget()
        wrapper.setObjectName("wrapper")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(20, 3, 3, 3)
        wrapper_layout.addWidget(w.native)  # type: ignore[attr-defined]
        wrapper.setStyleSheet("""
            #wrapper {
                border: 1px solid #00876C;
                border-radius: 8px;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 135, 108, 1),
                    stop:0.05 rgba(0, 135, 108, 0),
                    stop:1 rgba(0, 135, 108, 0)
                );
            }
        """)
        inner_layout.addWidget(wrapper)

    inner_layout.addStretch()

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner_widget)
    scroll.setMinimumWidth(370)

    scrolltab = scroll

    return scrolltab
