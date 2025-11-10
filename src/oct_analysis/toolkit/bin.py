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
from napari.utils.notifications import show_info


def increase_contrast(stack: np.ndarray, percentile: float) -> np.ndarray:
    nonzero_values = stack[stack > 0]  # Extract non-zero values
    min_val = np.percentile(
        nonzero_values, percentile
    )  # Find the 1st percentile without zeros
    max_val = np.percentile(stack, 100 - percentile)
    if max_val == min_val:
        show_info("Image has no contrast to enhance.")
        return stack

    contrast_enhanced = np.clip(((stack - min_val) / (max_val - min_val)), 0, 1)
    return contrast_enhanced


def plot_histograms(original: np.ndarray, new: np.ndarray, percentile: float):
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.hist(
        original.ravel(), bins=256, range=(0, 1), color="blue", alpha=0.7, log=True
    )
    plt.title("Original image histogram")
    plt.xlabel("Pixel intensity")
    plt.ylabel("Pixel amount")

    plt.subplot(1, 2, 2)
    plt.hist(new.ravel(), bins=256, range=(0, 1), color="green", alpha=0.7, log=True)
    plt.title(f"Contrast enhanced image histogram with percentile {percentile}")
    plt.xlabel("Pixel intensity")
    plt.ylabel("Pixel amount")
    plt.show()


def get_threshold(stack: np.ndarray) -> float:
    """
    Create a binary mask from an image stack, ignoring zero pixels.
    """

    nonzero_values = stack[stack > 0]  # Extract non-zero values

    thresh = filters.threshold_otsu(nonzero_values)

    return thresh


def rm_outliers(stack: np.ndarray, size: int) -> np.ndarray:
    bool_stack = stack.astype(bool)

    stack_transformed = morphology.remove_small_objects(
        bool_stack, size, connectivity=1
    )

    stack = stack_transformed.astype(np.uint8)

    return stack
