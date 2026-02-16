"""
Can read:
- Thorlabs OCT file format: [.oct]
    -> single files
    -> multiple files from a folder
"""

import bio_oct
from typing import Callable
from pathlib import Path


def get_reader_fn(path: str | list[str]) -> Callable | None:
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]

    # the get_reader function should make as many checks as possible
    # (without loading the full file) to determine if it can read
    # the path.
    if not Path(path).suffix == ".oct":
        return None

    # napari_get_reader should never raise an exception, because napari
    # raises its own specific errors depending on what plugins are
    # available for the given path, so we catch
    # any errors here and return None.

    # otherwise we return the *function* that can read ``path``.
    return read_oct


def read_oct(path):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """

    # handle both single path and list of paths
    paths = [path] if isinstance(path, str) else path

    # load all files
    image_data_list = [bio_oct.ThorlabsOCT(_path) for _path in paths]

    # convert to LayerData tuples
    layer_data = []
    for image_data in image_data_list:
        data = image_data.stack  # numpy array
        metadata = {
            "affine": image_data.affine,
            "metadata": {  # compatible with napari-nifti _writer
                "spacing": image_data.spacing,
                "origin": image_data._origin,
                "direction": image_data._direction,
                "header": None,  # needed for compatibility
                "oct_header": image_data.header_str,
            },
        }
        layer_type = "image"

        layer_data.append((data, metadata, layer_type))

    return layer_data
