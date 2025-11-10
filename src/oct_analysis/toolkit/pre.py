import scipy.ndimage
import numpy as np
from typing import Callable, cast


def zero_out_ignored_slices(stack: np.ndarray, ignored_slices: list[int]) -> np.ndarray:
    if not isinstance(ignored_slices, list):
        raise TypeError("ignored_slices must be a list of integers.")

    if not all(isinstance(i, int) for i in ignored_slices):
        raise ValueError("All elements in ignored_slices must be integers.")

    copy = stack.copy()
    copy[ignored_slices, :, :] = 0  # Zero out specified slices
    return copy


def median_blur(stack: np.ndarray, filter_size: int) -> np.ndarray:
    return scipy.ndimage.median_filter(
        stack, size=(1, filter_size, filter_size)
    )  # filterplane=2D (xz), not filtering depth (y) since it's anistropic to xz


def roi_filter_2D(stack: np.ndarray, roi_size: int) -> np.ndarray:
    # cast uniform_filter auf Callable, das tuple[int,int] erlaubt
    uniform_filter_fn = cast(Callable[..., np.ndarray], scipy.ndimage.uniform_filter)

    return uniform_filter_fn(
        stack, size=(roi_size, roi_size), axes=(0, 2), mode="reflect"
    )


def locate_window(stack: np.ndarray, ymin: int, ymax: int, y_offset: int) -> np.ndarray:
    y_coords = np.argmax(stack[:, ymin:ymax, :], axis=1)
    y_coords += y_offset + ymin

    return y_coords


def zero_out_window(stack: np.ndarray, window_coords: np.ndarray | None) -> np.ndarray:
    if window_coords is None:
        raise ValueError("window_coords is None.")

    yy = np.arange(stack.shape[1])  # Create a range for y-coordinates
    yy = yy.reshape(1, -1, 1)  # Reshape to ensure it can be broadcasted
    copy = stack.copy()  # Create a copy of the image to avoid modifying the original
    copy[yy < window_coords[:, np.newaxis, :]] = (
        0  # Set pixels above the window to zero
    )
    return copy


def locate_substratum(
    stack: np.ndarray, ymin: int, ymax: int, y_offset: int
) -> np.ndarray:
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
    copy = stack.copy()  # Create a copy of the image to avoid modifying the original
    copy[yy >= substratum_coords[:, np.newaxis, :]] = (
        0  # Set pixels below the substratum to zero
    )
    return copy
