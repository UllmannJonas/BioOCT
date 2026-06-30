from typing import cast, TYPE_CHECKING
import numpy as np
from skimage.measure import label
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import napari.layers


def scale1000(image: "napari.layers.Layer") -> None:
    image.scale = np.asarray([1000, 1000, 1000])
    image.refresh()


def plot_connected_components(image: "napari.layers.Labels") -> None:
    all_sizes = []
    for bscan in range(image.data.shape[0]):
        labels = cast(np.ndarray, label(image.data[bscan], connectivity=2))
        sizes = np.bincount(labels.ravel())[1:]
        all_sizes.append(sizes)

    all_sizes = np.concatenate(all_sizes)

    #! how to make bins=number of component sizes
    plt.hist(all_sizes, bins=500)
    plt.xlabel("Component size (pixels)")
    plt.ylabel("Frequency")
    plt.title("Component Size Distribution (per-slice)")
    plt.show(block=False)
