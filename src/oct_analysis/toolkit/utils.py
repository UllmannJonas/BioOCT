"""
Helper functions for oct_analysis toolkit.
>DRY - Don't Repeat Yourself<
"""

# Python native imports
from typing import Literal
from functools import wraps
import warnings
import traceback

# Third party imports
import numpy as np
from qtpy.QtWidgets import QMessageBox


# Checks whether a given stack is binarized (contains only 0 and 1 values)
def binary_check(binarized_stack: np.ndarray):
    if not set(np.unique(binarized_stack)).issubset({0, 1}):
        raise ValueError(
            "Passed stack is not binarized, contains values unequal to 0 or 1."
        )


# Checks layer existence for certain functions as precondition
def layer_exists_check(viewer, layer_name: str):
    if layer_name not in viewer.layers:
        raise ValueError(f"Layer missing for this operation: {layer_name}.")


# Updates or creates an image layer in the napari viewer
def update_layer(
    viewer,
    data: np.ndarray,
    type: Literal["image", "label"] = "image",
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
def vizualize_coords(
    stack: np.ndarray, coord_array: np.ndarray, pixel_value: int
) -> np.ndarray:
    z, x = coord_array.shape
    y = stack.shape[1]
    label_stack = np.zeros((z, y, x), dtype=np.uint8)
    z_idx, x_idx = np.meshgrid(np.arange(z), np.arange(x), indexing="ij")
    y_idx = coord_array
    mask = (y_idx >= 0) & (y_idx < y)  # ensure indices are within bounds
    label_stack[z_idx[mask], y_idx[mask], x_idx[mask]] = pixel_value

    return label_stack


# Decorator for error handling in GUI functions
def gui_error_handler(func):
    """
    Decorator to handle errors and warnings in GUI functions.
    - Exceptions: show critical QMessageBox and stop execution.
    - Warnings: show warning QMessageBox but continue execution.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                tb = traceback.format_exc()

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Error!")
                msg.setText(f"Execution was stopped!\nERROR: {str(e)}")
                msg.setDetailedText(tb)
                msg.setMinimumSize(500, 200)  # Breite/Höhe anpassen
                msg.exec()

            for w in caught_warnings:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Warning!")
                msg.setText(
                    f"Execution continued, but something happened:\nWARNING: {str(w.message)}"
                )
                msg.setMinimumSize(500, 200)  # Breite/Höhe anpassen
                msg.exec()

            return result

    return wrapper
