"""
Module containing pre-processing functions to remove all image objects other than biofilm and background.
"""

# Python native imports
from typing import Callable, cast

# Third-party imports
import scipy.ndimage
import numpy as np


# Filters
def reduce_stack(stack: np.ndarray, xstart: int, xend: int) -> np.ndarray:
    if xstart > xend:
        raise ValueError(
            f"Slice range invalid:\nFirst Slice={xstart}\nLast Slice={xend}"
        )
    keep_slices = list(range(xstart, xend + 1))
    return stack[keep_slices, :, :]


def median_blur(stack: np.ndarray, filter_size: int) -> np.ndarray:
    # filterplane=2D (xz), not filtering depth (y) since it's anistropic to xz
    filtered_stack = scipy.ndimage.median_filter(
        stack, size=(1, filter_size, filter_size)
    )

    filtered_stack[stack == 0] = 0

    return filtered_stack


def roi_filter_2D(stack: np.ndarray, roi_size: int) -> np.ndarray:
    # cast uniform_filter auf Callable, das tuple[int,int] erlaubt
    uniform_filter_fn = cast(Callable[..., np.ndarray], scipy.ndimage.uniform_filter)

    filtered_stack = uniform_filter_fn(
        stack,
        size=(roi_size, roi_size),
        axes=(0, 2),  # filterplane xz
    )

    filtered_stack[stack == 0] = 0

    return filtered_stack


# Locate and remove objects
def locate_window(stack: np.ndarray, ymin: int, ymax: int, y_offset: int) -> np.ndarray:
    if ymin >= ymax:
        raise ValueError(f"ymin must be less than ymax.\nymin={ymin}\nymax={ymax}")

    y_coords = np.argmax(stack[:, ymin:ymax, :], axis=1)
    y_coords = y_coords + y_offset + ymin

    return y_coords


def get_cutoff(stack: np.ndarray, cutoff_y: int) -> np.ndarray:
    z, _, x = stack.shape
    return np.full((z, x), cutoff_y, dtype=int)


def zero_out_window(stack: np.ndarray, window_coords: np.ndarray | None) -> np.ndarray:
    if window_coords is None:
        raise ValueError("window_coords is None.")

    yy = np.arange(stack.shape[1])  # Create a range for y-coordinates
    yy = yy.reshape(1, -1, 1)  # Reshape to ensure it can be broadcasted
    stack[yy < window_coords[:, np.newaxis, :]] = (
        0  # Set pixels above the window to zero
    )
    return stack


def locate_substratum(
    stack: np.ndarray, ymin: int, ymax: int, y_offset: int
) -> np.ndarray:
    if ymin >= ymax:
        raise ValueError(f"ymin must be less than ymax.\nymin={ymin}\nymax={ymax}")

    y_coords = np.argmax(stack[:, ymin:ymax, :], axis=1)
    y_coords = y_coords + ymin + y_offset

    return y_coords


def zero_out_substratum(
    stack: np.ndarray, substratum_coords: np.ndarray | None
) -> np.ndarray:
    if substratum_coords is None:
        raise ValueError("substratum_coords is None.")

    yy = np.arange(stack.shape[1])  # Create a range for y-coordinates
    yy = yy.reshape(1, -1, 1)  # Reshape to ensure it can be broadcasted
    stack[yy >= substratum_coords[:, np.newaxis, :]] = (
        0  # Set pixels below the substratum to zero
    )
    return stack
