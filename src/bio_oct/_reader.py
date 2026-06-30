"""
Can read:
- Thorlabs OCT file format: [.oct]
    -> single files
    -> multiple files from a folder
"""

from __future__ import annotations
from typing import Callable, Tuple
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
from numpy.typing import NDArray


class ThorlabsOCT:
    """Loads an .oct file from its path as an image object.

    Object Attributes:
        stack (NDArray[np.float32]): The loaded image stack as a numpy array.
        spacing (np.ndarray): The pixel spacing in mm for each dimension.
        ndims (int): The number of dimensions of the image stack.
        affine (np.ndarray): The affine transformation matrix for the image stack.
        header_str (str): The raw XML header as a string.
    """

    def __init__(self, filepath: Path | str) -> None:
        # validate filepath
        if Path(filepath).suffix.lower() != ".oct":
            raise ValueError("File extension is not <.oct>. Unable to process file.")

        # validate contents
        with zipfile.ZipFile(filepath, "r") as z:
            items = z.namelist()
        if next((item for item in items if "Header" in item), None) is None:
            raise FileNotFoundError("Header.xml not found in OCT file.")
        if next((item for item in items if "Intensity" in item), None) is None:
            raise FileNotFoundError("Intensity.data not found in OCT file.")

        # load data from file
        self.stack, self._spacing, self._ndims, self.header_str = self._load(filepath)
        self._origin = np.zeros(self.ndims)  # assume origin at (0,0,0)
        self._direction = np.eye(self.ndims)  # assume no rotation -> identity matrix
        self.source_dir = Path(filepath).parent
        self.filename = Path(filepath).stem

    @property
    def ndims(self) -> int:
        return self._ndims

    @property
    def spacing(self) -> np.ndarray:
        return self._spacing

    @property
    def affine(self) -> np.ndarray:
        _affine = np.eye(self.ndims + 1)
        _affine[: self.ndims, : self.ndims] = self._direction @ np.diag(self.spacing)
        _affine[: self.ndims, self.ndims] = self._origin
        return _affine

    def _get_xmlelement(self, root, path, cast=str):
        element = root.find(path)
        return cast(element.text) if element is not None else 0

    #! 2D support, needs testing after v0.4.0
    #! def _get_spacing(self, header_root, is_2d: bool = False) -> np.ndarray:
    def _get_spacing(self, header_root) -> np.ndarray:
        spacing = {
            "b_scans": float(
                self._get_xmlelement(header_root, path="Image/PixelSpacing/SizeY")
            ),
            "axial": float(
                self._get_xmlelement(header_root, path="Image/PixelSpacing/SizeZ")
            ),
            "lateral": float(
                self._get_xmlelement(header_root, path="Image/PixelSpacing/SizeX")
            ),
        }
        if any(v == 0.0 for v in spacing.values()):
            # Fallback calculation falls PixelSpacing = 0:
            fov = {
                "b_scans": float(
                    self._get_xmlelement(header_root, path="Image/SizeReal/SizeY")
                ),
                "axial": float(
                    self._get_xmlelement(header_root, path="Image/SizeReal/SizeZ")
                ),
                "lateral": float(
                    self._get_xmlelement(header_root, path="Image/SizeReal/SizeX")
                ),
            }
            shape = {
                "b_scans": int(
                    self._get_xmlelement(header_root, path="Image/SizePixel/SizeY")
                ),
                "axial": int(
                    self._get_xmlelement(header_root, path="Image/SizePixel/SizeZ")
                ),
                "lateral": int(
                    self._get_xmlelement(header_root, path="Image/SizePixel/SizeX")
                ),
            }
            for axis in ["b_scans", "axial", "lateral"]:
                if shape[axis] > 0 and fov[axis] > 0:
                    spacing[axis] = fov[axis] / shape[axis]
                #! 2D support, needs testing after v0.4.0
                #! elif is_2d and axis == "b_scans":  # Mode2D has no SizeY in header -> lateral spacing as fallback
                #!     spacing[axis] = spacing["lateral"] if spacing["lateral"] > 0.0 else 0.01
                else:
                    return np.array([0.01, 0.01, 0.01])

        # convert spacing to np.ndarray in order of B-Scans, Axial, Lateral
        return np.array(
            [spacing["b_scans"], spacing["axial"], spacing["lateral"]]
        ).astype(float)

    def _normalize(self, stack: NDArray) -> NDArray[np.float32]:
        stack = stack.astype(np.float32, copy=False)
        stack -= np.min(stack)
        stack /= np.max(stack)

        return stack

    def _load(
        self, filepath: Path | str
    ) -> Tuple[NDArray[np.float32], np.ndarray, int, str]:
        with zipfile.ZipFile(filepath, "r") as z:
            items = z.namelist()
            header = next(item for item in items if "Header" in item)
            intensity = next(item for item in items if "Intensity" in item)

            with z.open(header) as h:
                tree = ET.parse(h)
                header_root = tree.getroot()
                header_str = ET.tostring(header_root, encoding="unicode")

            with z.open(intensity) as i:
                intensity_raw = i.read()

        #! 2D support, needs testing after v0.4.0
        #! detect 2D acquisition (singe B-Scan)
        #! is_2d = (self._get_xmlelement(header_root, path="MetaInfo/AcquisitionMode") == "Mode2D")

        # safe metadata in same order that is used internally for correct referencing
        shape = (
            #! 2D support, needs testing after v0.4.0
            #! b_scans: explicitly 1 for Mode2D, otherwise read from header
            #! 1 if is_2d else int(self._get_xmlelement(header_root, path="Image/SizePixel/SizeY")),
            int(self._get_xmlelement(header_root, path="Image/SizePixel/SizeY")),
            # axial (a-scan depth)
            int(self._get_xmlelement(header_root, path="Image/SizePixel/SizeZ")),
            # lateral (a-scan index)
            int(self._get_xmlelement(header_root, path="Image/SizePixel/SizeX")),
        )

        ndims = len(shape)

        spacing = self._get_spacing(header_root)
        #! 2D support needs testing after v0.4.0
        #! spacing = self._get_spacing(header_root, is_2d=is_2d)

        # shape as stored in Thorlabs OCT binary format due to physical scanning order
        # scanning laser goes: for every B-Scan (Y), for every lateral position (X), all axial points (Z)
        #! for Mode2D: binary data is just (lateral, axial), reshape to (1, lateral, axial)
        #! 2D support needs testing after v0.4.0
        #! if is_2d:
        #     shape_thorlabs = (shape[2], shape[1])
        #     stack = (
        #         np.frombuffer(intensity_raw, dtype=np.float32)
        #         .copy()
        #         .reshape(shape_thorlabs)
        #         .transpose(1, 0)  # -> (axial, lateral)
        #         [np.newaxis, :, :]  # -> (1, axial, lateral)
        #     )
        # else:
        shape_thorlabs = (shape[0], shape[2], shape[1])
        stack = (
            np.frombuffer(intensity_raw, dtype=np.float32)
            .copy()
            .reshape(shape_thorlabs)
            # transpose to ZYX or B-Scans, Axial, Lateral for visualization in napari "left-handedness"
            .transpose(0, 2, 1)
        )

        return self._normalize(stack), spacing, ndims, header_str


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


def read_oct(path: str | list[str]):
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
    oct_files = [ThorlabsOCT(_path) for _path in paths]

    # convert to LayerData tuples
    layer_data = []
    for oct in oct_files:
        data = (oct.stack * 255).astype(np.uint8)  # convert to uint8 for plugin
        napari_metadata = {
            "axis_labels": ("B-Scans", "Axial (depth)", "Lateral"),
            "affine": oct.affine,
            "units": ("µm", "µm", "µm"),
            "contrast_limits": (0, 255),
            "scale": (
                1000,
                1000,
                1000,
            ),  # convert from mm to µm for napari visualization
            "metadata": {  # = layer.metadata
                "spacing": oct.spacing.tolist(),
                "origin": oct._origin,
                "direction": oct._direction,
                "header": None,  # needed for compatibility with napari-nifti _writer
                "source_dir": str(oct.source_dir),
                "filename": str(oct.filename),
            },
        }
        layer_type = "image"

        layer_data.append((data, napari_metadata, layer_type))

    return layer_data
