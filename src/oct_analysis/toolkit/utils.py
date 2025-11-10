"""
Helper functions for oct_analysis toolkit.
>DRY - Don't Repeat Yourself<
"""

# Python native imports
from typing import Literal
from functools import wraps

# Third party imports
import numpy as np
from magicgui.widgets import Container
from qtpy.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QMessageBox

# Local imports
from oct_analysis.napari_plugin import widgets


# Checks whether a given stack is binarized (contains only 0 and 1 values)
def binary_check(binarized_stack: np.ndarray):
    if not set(np.unique(binarized_stack)).issubset({0, 1}):
        raise ValueError(
            "Passed stack is not binarized, contains values unequal to 0 or 1."
        )


# Updates or creates an image layer in the napari viewer
def update_layer(
    viewer,
    data: np.ndarray,
    type: Literal["image", "label"],
    metadata: dict | np.ndarray | None = None,
    name: str = "",
    visible=True,
) -> None:
    if name in viewer.layers:
        layer = viewer.layers[name]
        layer.data = data
    else:
        if type == "label":
            viewer.add_labels(data, name=name, visible=visible)
        else:
            viewer.add_image(data, name=name, visible=visible)

    if metadata is not None:
        layer = viewer.layers[name]
        layer.metadata = metadata


# Create a label stack from coordinate array for visualization
def vizualize_coords(stack, coord_array, pixel_value):
    z, x = coord_array.shape
    y = stack.shape[1]
    label_stack = np.zeros((z, y, x), dtype=np.uint8)
    z_idx, x_idx = np.meshgrid(np.arange(z), np.arange(x), indexing="ij")
    y_idx = coord_array
    mask = (y_idx >= 0) & (y_idx < y)  # ensure indices are within bounds
    label_stack[z_idx[mask], y_idx[mask], x_idx[mask]] = pixel_value

    return label_stack


# Creates a scrollable tab containing the provided widgets for napari plugin GUI
def create_scrolltab(
    widget_list: list, name: str = "", min_width: int = 500
) -> QScrollArea:
    container = Container(
        widgets=widget_list, layout="vertical", name=name, visible=True, labels=False
    )

    inner_widget = QWidget()
    inner_layout = QVBoxLayout(inner_widget)
    inner_layout.addWidget(container.native)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(inner_widget)
    scroll.setMinimumWidth(min_width)

    scrolltab = scroll

    return scrolltab


# Decorator for error handling in GUI functions
def gui_error_handler(func):
    """
    Decorator to handle errors in GUI functions and display them using a QMessageBox.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))

    return wrapper


## Create widget list for settings
def get_setting_widgets() -> list:
    settings_widgets = [  # Needs to be updated if new widgets are added
        widgets.handle_input,
        widgets.median_filter,
        widgets.roi_filter_2D,
        widgets.locate_window,
        widgets.locate_substratum,
        widgets.increase_contrast,
        widgets.auto_threshold,
        widgets.remove_outliers,
    ]

    return settings_widgets
