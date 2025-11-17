"""
Utility functions for napari plugin.
Includes:
- File loading functions for NIfTI, OCT, and TIFF files.
- File saving functions for NIfTI and TIFF files.
- Settings loading and saving functions.
"""

# python native imports
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Callable
import warnings

# third-party imports
import nibabel as nib
import numpy as np
from numpy.typing import NDArray
import tifffile as tiff


# Functions for loading files
def get_load_fn(filepath: Path) -> Callable:
    ext = "".join(filepath.suffixes).lower()
    if ext in [".nii", ".nii.gz", ".niigz"]:
        return load_nifti
    elif ext == ".oct":
        return load_oct
    elif ext in [".tif", ".tiff"]:
        return load_tif
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def load_oct(filepath: Path) -> tuple[np.ndarray, dict]:
    with zipfile.ZipFile(filepath, "r") as z:
        items = z.namelist()

        header = next((item for item in items if "xml" in item), None)
        intensity = next((item for item in items if "Intensity" in item), None)
        # elif "Video" in item:
        #     videoimg = item

        # get metadata
        if header is None:
            raise FileNotFoundError("Header.xml not found in OCT file.")

        with z.open(header) as xmlf:
            tree = ET.parse(xmlf)
            root = tree.getroot()

        def get(path, cast=str):
            element = root.find(path)
            return cast(element.text) if element is not None else 0

        try:
            meta = {  # TODO: get VideoImage metadata
                # safe metadata in same order that is used internally for correct referencing
                "dimensions_px": {
                    "B-Scans": int(get("Image/SizePixel/SizeY")),
                    "axial": int(get("Image/SizePixel/SizeZ")),
                    "lateral": int(get("Image/SizePixel/SizeX")),
                },
                "spacing_mm": {
                    "B-Scans": float(get("Image/PixelSpacing/SizeY")),
                    "axial": float(get("Image/PixelSpacing/SizeZ")),
                    "lateral": float(get("Image/PixelSpacing/SizeX")),
                },
                "filename": str(filepath.stem),
            }
            # Fallback calculation falls PixelSpacing = 0:
            fov = {
                "B-Scans": float(get("Image/SizeReal/SizeY")),
                "axial": float(get("Image/SizeReal/SizeZ")),
                "lateral": float(get("Image/SizeReal/SizeX")),
            }
            for axis in ["B-Scans", "axial", "lateral"]:
                if meta["spacing_mm"][axis] == 0.0:
                    if meta["dimensions_px"][axis] > 0 and fov[axis] > 0:
                        meta["spacing_mm"][axis] = (
                            fov[axis] / meta["dimensions_px"][axis]
                        )
                    else:
                        raise ValueError(
                            f"Invalid pixel size for axis: {axis}, fallback not possible"
                        )
        except Exception as e:
            raise RuntimeError(
                f"Failed while parsing metadata: {e}. Process terminated. Please check OCT header."
            ) from e

        # reformat intensity.data into np.ndarray
        if intensity is None:
            raise FileNotFoundError("Intensity data not found in OCT file.")

        with z.open(intensity) as f:
            intensity_data_raw = f.read()
        shape_thorlabs = (  # shape as stored in Thorlabs OCT binary format due to physical scanning order
            # scanning laser goes: for every B-Scan (Y), for every lateral position (X), all axial points (Z)
            meta["dimensions_px"]["B-Scans"],  # Y
            meta["dimensions_px"]["lateral"],  # X
            meta["dimensions_px"]["axial"],  # Z
        )
        intensity_data = (
            np.frombuffer(intensity_data_raw, dtype=np.float32)
            .copy()
            .reshape(shape_thorlabs)
        )
        # transpose to ZYX or B-Scans, Axial, Lateral for visualization in napari "left-handedness"
        # also use this order in all further processing steps as numpy array order
        intensity_data = intensity_data.transpose(0, 2, 1)

        # TODO: need metadata from VideoImage first
        # with z.open(videoimg) as f:
        #     videoimage_raw = f.read()
        # shape = (meta['videoimg']['width'], meta['videoimg']['height'], 4) # 4 channels (RGBA)
        # video_image = np.frombuffer(videoimage_raw, dtype=np.uint8).reshape(shape)

    meta = unify_metadata(meta)

    return intensity_data, meta  # video_image


def load_nifti(filepath: Path) -> tuple[np.ndarray, dict]:
    img = nib.nifti1.load(str(filepath))
    data = img.get_fdata(dtype=np.float32)

    if data.size == 0:
        raise ValueError(f"NIfTI file contains no data: {filepath}")
    if data.ndim != 3:
        raise ValueError(f"NIfTI file is not 3D: {filepath}")

    zooms_all = img.header.get_zooms()
    if len(zooms_all) < 3:
        raise ValueError(
            f"NIfTI file does not contain sufficient pixel spacing information: {filepath}"
        )
    zooms = zooms_all[:3]  # spacing_mm

    dims = data.shape

    try:
        meta = {
            "dimensions_px": {
                "B-Scans": dims[0],
                "axial": dims[1],
                "lateral": dims[2],
            },
            "spacing_mm": {
                "B-Scans": float(zooms[2]),
                "axial": float(zooms[1]),
                "lateral": float(zooms[0]),
            },
            "filename": str(filepath.name.replace(".nii.gz", "").replace(".nii", "")),
        }
    except Exception as e:
        raise RuntimeError(
            f"Failed while parsing metadata: {e}. Process terminated. Please check NIfTI header."
        ) from e

    meta = unify_metadata(meta)

    return data, meta


def load_tif(file_path: Path) -> tuple[np.ndarray, dict]:
    with tiff.TiffFile(file_path) as tif:
        stack = tif.asarray()

        if stack is None:
            raise ValueError(f"Failed to read image from {file_path}")

        meta = {}
        try:
            # Extract and parse ImageDescription metadata if available
            description = tif.pages[0].tags.get("ImageDescription")  # type: ignore
            if description:
                description_str = description.value
            else:
                raise ValueError("ImageDescription tag not found.")
        except Exception as e:
            raise RuntimeError(f"Failed to read ImageDescription tag: {e}") from e

        try:
            meta = json.loads(description_str)
        except json.JSONDecodeError:
            # Fallback: try to parse as ImageJ metadata
            ij_meta = {}
            for line in description_str.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    ij_meta[key.strip()] = value.strip()
            meta = {
                "dimensions_px": {
                    "B-Scans": int(ij_meta.get("slices", 1)),
                    "axial": int(ij_meta.get("ImageLength", 1)),
                    "lateral": int(ij_meta.get("ImageWidth", 1)),
                },
                "spacing_mm": {
                    "B-Scans": float(ij_meta.get("spacing", 1.0)),
                    "axial": float(ij_meta.get("spacing", 1.0)),
                    "lateral": float(ij_meta.get("spacing", 1.0)),
                },
                "filename": str(Path(file_path).stem),
            }
            warnings.warn(
                f"imagej metadata detected and used as fallback. pixel spacing is not correct: {meta['spacing_mm']}",
                UserWarning,
            )

    meta = unify_metadata(meta)

    return stack, meta


# Always normalize to [0,1]. all data that is loaded!
def normalize(stack: NDArray) -> NDArray[np.float32]:
    stack = stack.astype(np.float32)
    stack = (stack - np.min(stack)) / (np.max(stack) - np.min(stack))
    return stack


# Functions for saving files
def get_save_fn(stack: np.ndarray, metadata: dict | None, fmt: str) -> Callable:
    if metadata is None or not isinstance(metadata, dict):
        raise ValueError(
            "Metadata is required for saving. Metadata is currently None or invalid."
        )
    if not stack.size:
        raise ValueError("Stack is required for saving. Stack is currently empty.")

    if fmt in [".nii", ".nii.gz", ".niigz"]:
        return save_as_nifti
    elif fmt in [".tif", ".tiff"]:
        return save_as_tiff
    else:
        raise ValueError(f"Unsupported file format for saving: {fmt}")


def save_as_nifti(
    stack: np.ndarray, stack_metadata: dict, binary_stack: np.ndarray, output_dir: Path
) -> bool:
    spacing = stack_metadata["spacing_mm"]
    if any(v == 0 for v in spacing.values()):
        fallback_values = [0.01, 0.01, 0.01, 1.0]
        affine = np.diag(fallback_values)
        warnings.warn(
            f"[WARN]: Fallback values used for pixel spacing!\nValues used: {fallback_values}",
            UserWarning,
        )
    else:
        affine = np.diag(
            [
                spacing["lateral"],  # X
                spacing["axial"],  # Y
                spacing["B-Scans"],  # Z
                1.0,
            ]
        )

    nii_stack = nib.nifti1.Nifti1Image(stack.astype(np.float32), affine)
    nii_binary = nib.nifti1.Nifti1Image(binary_stack.astype(np.uint8), affine)

    # speichern
    output_dir.mkdir(parents=True, exist_ok=True)
    original_filepath = output_dir / f"{stack_metadata['filename']}.nii.gz"
    binary_filepath = output_dir / f"{stack_metadata['filename']}_mask.nii.gz"
    try:
        nib.save(nii_stack, original_filepath)  # type: ignore
        nib.save(nii_binary, binary_filepath)  # type: ignore
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to save NIfTI files: {e}") from e


def save_as_tiff(
    stack: np.ndarray, metadata: dict, binary_stack: np.ndarray, output_dir: Path
) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    path_original = output_dir / f"{metadata.get('filename', 'unknown')}.tiff"
    path_binary = output_dir / f"{metadata.get('filename', 'unknown')}_binary.tiff"

    try:
        with tiff.TiffWriter(path_original) as tif:
            tif.write(
                stack, photometric="minisblack", metadata=metadata
            )  # writes metadata as JSON
        with tiff.TiffWriter(path_binary) as bin_tif:
            bin_tif.write(
                binary_stack, photometric="minisblack", metadata=metadata
            )  # writes metadata as JSON
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to save TIFF files: {e}") from e


# Functions for saving/loading settings
def save_settings(
    output_dir,
    user_handle: str,
    setting_widgets: list,
    filename: str,
    thresholding_method: str | None = None,
) -> bool:
    match = re.search(r"_(\d+)_", filename)
    image_id = (
        match.group(1) if match else "unknown"
    )  # Read image ID from filename, e.g. "Mina_0054_Mode3D.oct" -> "0054"
    warnings.warn('Filename has no digit-ID, ID set to "unknown".')

    filename = f"settings_{image_id}_{user_handle}.json"
    settings_file = Path(output_dir) / filename

    settings = {}
    try:
        for widget in setting_widgets:
            params = {}
            # Die ursprünglichen Parameter stehen in __signature__.parameters
            for param in widget.__signature__.parameters:
                if param == "viewer":
                    continue  # viewer ist nicht serialisierbar
                w = widget.get_widget(param)
                if w is not None:
                    val = w.value
                    if isinstance(val, Path):
                        val = str(val)
                    params[param] = val
            settings[widget.name or widget.__class__.__name__] = params
        settings["thresholding_method"] = thresholding_method
    except Exception as e:
        raise RuntimeError(f"Error while collecting settings: {e}") from e

    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=4)
            return True
    except Exception as e:
        raise RuntimeError(f"Failed to save settings: {e}") from e


def load_settings(settings_file: Path) -> dict:
    if not settings_file.exists():
        raise FileNotFoundError(f"Settings file not found: {settings_file}")

    with open(settings_file, "r") as f:
        settings = json.load(f)

    return settings


# Helpers used only here


## Unify metdata
def unify_metadata(meta: dict) -> dict:
    """
    Keep only 'dimensions_px', 'spacing_mm', 'filename'.
    Round floats in spacing_mm to 5 decimals.
    Example metadata dict:
    {
        'dimensions_px': {
            'B-Scans': 750,
            'axial': 520,
            'lateral': 500
        },
        'spacing_mm': {
            'B-Scans': 0.00733,
            'axial': 0.00417,
            'lateral': 0.01700
        },
        'filename': 'test-napari'
    }
    """
    unified = {
        "dimensions_px": meta.get("dimensions_px", {}),
        "spacing_mm": {
            k: round(float(v), 5) for k, v in meta.get("spacing_mm", {}).items()
        },
        "filename": meta.get("filename", ""),
    }
    return unified
