"""
Functions for binarization of pre-processed OCT-Scans, called by napari plugin widgets.
The functions rely on an image structure with only biofilm and background noise left,
with the rest of the image zeroed out.

Includes:
- Finding substratum and replacing everything below with zeros
- Finding windows and replacing everything above with zeros
- Contrast enhancement for better thresholding
- Thresholding using Yen's or Otsu's method
- Removal of small objects (outliers) from binary masks
"""

# Third party imports
import numpy as np
import matplotlib.pyplot as plt
from skimage import filters, morphology

# Local imports
from oct_analysis.toolkit.utils import binary_check


def increase_contrast(stack: np.ndarray, percentile: float) -> np.ndarray:
    nonzero_stack = stack[stack > 0]  # Extract non-zero values

    # Find the 1st percentile without zeros
    min_val = np.percentile(nonzero_stack, percentile)
    max_val = np.percentile(nonzero_stack, 100 - percentile)

    contrast_enhanced = np.clip(((stack - min_val) / (max_val - min_val)), 0, 1)
    return contrast_enhanced


def get_threshold(stack: np.ndarray) -> dict:
    """
    Create a binary mask from an image stack, ignoring zero pixels.
    """

    # Check for RGB image/stack
    if stack.ndim == 3 and stack.shape[-1] == 3:
        raise ValueError("Input appears to be RGB, expected grayscale.")
    if stack.ndim == 4 and stack.shape[-1] == 3:
        raise ValueError("Input appears to be RGB stack, expected grayscale stack.")

    values = stack[(stack > 0) & (stack < 1)]

    methods = {
        "otsu": filters.threshold_otsu,
        "yen": filters.threshold_yen,
        "li": filters.threshold_li,
        "triangle": filters.threshold_triangle,
        "isodata": filters.threshold_isodata,
    }

    thresholds = {}
    for name, func in methods.items():
        thresholds[name] = float(func(values))

    colors = ["red", "blue", "green", "purple", "orange"]
    _, ax = plt.subplots()
    ax.hist(values, bins=512, color="gray", alpha=0.7)
    for i, (name, thresh) in enumerate(thresholds.items()):
        ax.axvline(thresh, color=colors[i], label=f"{name}: {thresh:.2f}")
    ax.set_xlabel("Pixel Intensity")
    ax.set_ylabel("Frequency (log-scale)")
    ax.set_yscale("log")
    ax.legend()
    ax.set_title("Threshold Results")
    plt.show()

    return thresholds


def rm_outliers(stack: np.ndarray, size: int) -> np.ndarray:
    binary_check(stack)

    bool_stack = stack.astype(bool)

    stack_transformed = morphology.remove_small_objects(
        bool_stack, size, connectivity=1
    )

    stack = stack_transformed.astype(np.uint8)

    return stack
