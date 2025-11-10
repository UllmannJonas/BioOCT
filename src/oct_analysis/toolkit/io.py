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

# third-party imports
from napari.utils.notifications import show_error
import nibabel as nib
import numpy as np
from numpy.typing import NDArray
import tifffile as tiff


# Functions for loading files
def get_load_fn(filepath: Path) -> Callable:
    """
    Get the appropriate loading function based on the file extension.
    Also checks if file exists.

    Parameters
    ----------
    filepath : Path
        Path to the file.

    Returns
    -------
    Callable
        A function that can load the file.
        Possible returned functions: load_nifti, load_oct, load_tif
    """

    if not filepath.exists():
        show_error("File does not exist.")
        raise FileNotFoundError(f"File not found: {filepath}")

    ext = "".join(filepath.suffixes).lower()
    if ext in [".nii", ".nii.gz", ".niigz"]:
        return load_nifti
    elif ext == ".oct":
        return load_oct
    elif ext in [".tif", ".tiff"]:
        return load_tif
    else:
        show_error(f"Unsupported file extension: {ext}")
        raise ValueError(f"Unsupported file extension: {ext}")


def load_nifti(filepath: Path) -> tuple[np.ndarray, dict]:
    """
    Load a NIfTI file and return the image data and metadata.

    Parameters
    ----------
    filepath : Path
        Path to the NIfTI file.

    Returns
    -------
    tuple
        A tuple containing:
        - numpy.ndarray: The image data as a numpy array.
        - dict: Metadata including size, spacing, and filename.
    """

    img = nib.nifti1.load(str(filepath))
    data = img.get_fdata(dtype=np.float32)
    header = img.header

    meta = {
        "size_px": {
            "x": int(header["dim"][1]),
            "z": int(header["dim"][2]),
            "y": int(header["dim"][3]),
        },
        "spacing_mm": {
            "x": float(header.get_zooms()[0]),
            "y": float(header.get_zooms()[1]),  # type: ignore
            "z": float(header.get_zooms()[2]),  # type: ignore
        },
        "filename": str(filepath.stem),
    }

    return data, meta


def load_oct(filepath: Path) -> tuple[np.ndarray, dict]:
    """
    Load an OCT file and extract its intensity data and metadata.

    Parameters
    ----------
    filepath : Path
        The path to the OCT file.

    Returns
    -------
    tuple
        A tuple containing the intensity data as a numpy array and a dictionary of metadata.
    """

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
                "size_px": {
                    "z": int(get("Image/SizePixel/SizeZ")),
                    "y": int(get("Image/SizePixel/SizeY")),
                    "x": int(get("Image/SizePixel/SizeX")),
                },
                "fov_mm": {
                    "z": float(get("Image/SizeReal/SizeZ")),
                    "y": float(get("Image/SizeReal/SizeY")),
                    "x": float(get("Image/SizeReal/SizeX")),
                },
                "spacing_mm": {
                    "z": float(get("Image/PixelSpacing/SizeZ")),
                    "y": float(get("Image/PixelSpacing/SizeY")),
                    "x": float(get("Image/PixelSpacing/SizeX")),
                },
                "instrument": {
                    "model": get("Instrument/Model"),
                    "serial": get("Instrument/Serial"),
                    "central_wavelength": float(get("Instrument/CentralWavelength")),
                },
                "dtype": get("Image/DataType"),
                "timestamp": int(get("Acquisition/Timestamp")),
                "filename": str(Path(filepath).stem),
            }
            # Fallback falls PixelSpacing = 0:
            for axis in ["x", "y", "z"]:
                if meta["spacing_mm"][axis] == 0.0:
                    if meta["size_px"][axis] > 0 and meta["fov_mm"][axis] > 0:
                        meta["spacing_mm"][axis] = (
                            meta["fov_mm"][axis] / meta["size_px"][axis]
                        )
                    else:
                        print(
                            f"[WARN] Invalid pixel size for axis {axis}, fallback not possible"
                        )

        except (TypeError, ValueError, AttributeError) as e:
            print(
                f"[ERROR] Failed while parsing metadata: {e}. Process terminated. Please check Header.xml file."
            )
            return  # type: ignore

        # reformat intensity.data into np.ndarray
        if intensity is None:
            raise FileNotFoundError("Intensity data not found in OCT file.")
        with z.open(intensity) as f:
            intensity_data_raw = f.read()
        shape = (
            meta["size_px"]["y"],
            meta["size_px"]["x"],
            meta["size_px"]["z"],
        )  # ZXY
        intensity_data = (
            np.frombuffer(intensity_data_raw, dtype=np.float32).copy().reshape(shape)
        )
        intensity_data = intensity_data.transpose(0, 2, 1)

        # TODO: need metadata from VideoImage first
        # with z.open(videoimg) as f:
        #     videoimage_raw = f.read()
        # shape = (meta['videoimg']['width'], meta['videoimg']['height'], 4) # 4 channels (RGBA)
        # video_image = np.frombuffer(videoimage_raw, dtype=np.uint8).reshape(shape)

    return intensity_data, meta  # video_image


def load_tif(file_path: Path) -> tuple[np.ndarray, dict]:
    """
    Load a TIFF file and extract its image data and metadata.

    Parameters
    ----------
    file_path : Path
        The path to the TIFF file.

    Returns
    -------
    tuple
        A tuple containing the image data as a numpy array and a dictionary of metadata.
    """

    with tiff.TiffFile(file_path) as tif:
        page = tif.pages[0]  # first page
        tags = page.tags  # type: ignore

        # Extract and parse ImageDescription metadata if available
        description = tags.get("ImageDescription")  # type: ignore
        imagej_metadata = {}
        if description:
            for line in description.value.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    imagej_metadata[key.strip()] = value.strip()

        # Read stack data
        stack = tif.asarray()
        if stack is None:
            raise ValueError(f"Failed to read image from {file_path}")
        if stack.dtype != np.float32:
            raise ValueError(f"Image stack is not in float32 format: {file_path}")

        # Parse ImageJ metadata
        metadata = {
            "Z": int(imagej_metadata.get("slices", 1)),
            "Y": page.tags["ImageLength"].value,  # type: ignore
            "X": page.tags["ImageWidth"].value,  # type: ignore
            "shape": tif.series[0].shape,
            "dtype": str(tif.series[0].dtype),
            "axes": tif.series[0].axes,
            "XResolution": page.tags["XResolution"].value,  # type: ignore
            "YResolution": page.tags["YResolution"].value,  # type: ignore
            "unit": imagej_metadata.get("unit", None),
            "spacing": float(imagej_metadata.get("spacing", 1.0)),
        }

    return stack, metadata


# Always normalize to [0,1]. all data that is loaded!
def normalize(stack: NDArray[np.float32]) -> NDArray[np.float32]:
    stack_norm = (stack - np.min(stack)) / (np.max(stack) - np.min(stack))
    return stack_norm.astype(np.float32)


# Functions for saving files
def get_save_fn(stack: np.ndarray, metadata: dict | None, fmt: str) -> Callable:
    """
    Get the appropriate saving function based on the selected file format.

    Parameters
    ----------
    stack : np.ndarray
        The image stack to be saved.
    metadata : dict | None
        Metadata associated with the image stack.
    fmt : str
        The desired file format for saving (e.g., ".nii", ".tif").

    Returns
    -------
    Callable
        A function that can save the file.
        Possible returned functions: save_as_nifti, save_as_tiff
    """

    if metadata is None or not isinstance(metadata, dict):
        show_error(
            "Metadata is required for saving. Error in metadata format/existence."
        )
        raise ValueError("Metadata is required for saving.")
    if not stack:
        show_error("Stack is required for saving.")
        raise ValueError("Stack is required for saving.")

    if fmt in [".nii", ".nii.gz", ".niigz"]:
        return save_as_nifti
    elif fmt in [".tif", ".tiff"]:
        return save_as_tiff
    else:
        show_error(f"Unsupported file format for saving: {fmt}")
        raise ValueError(f"Unsupported file format for saving: {fmt}")


def save_as_nifti(
    stack: np.ndarray, stack_metadata: dict, binary_stack: np.ndarray, output_dir: Path
) -> bool:
    """
    Save the image stack and its binary mask as NIfTI files.

    Parameters
    ----------
    stack : np.ndarray
        The image stack to be saved.
    stack_metadata : dict
        Metadata associated with the image stack.
    binary_stack : np.ndarray
        The binary mask of the image stack to be saved.
    output_dir : Path
        The directory where the NIfTI files will be saved.

    Returns
    -------
    bool
        True if saving was successful, False otherwise.
    """

    spacing = stack_metadata["spacing_mm"]
    if any(v == 0 for v in spacing.values()):
        affine = np.diag([0.01, 0.01, 0.01, 1.0])
        print("[WARN]: Fallback values used for pixel spacing!")
    else:
        affine = np.diag([spacing["x"], spacing["y"], spacing["z"], 1.0])

    nii_stack = nib.nifti1.Nifti1Image(stack.astype(np.float32), affine)
    nii_binary = nib.nifti1.Nifti1Image(binary_stack.astype(np.uint8), affine)

    # metadaten für nifti header
    model = stack_metadata["instrument"]["model"]
    wl = stack_metadata["instrument"]["central_wavelength"]
    timestamp = stack_metadata["timestamp"]
    descrip = f"{model}_{wl:.0f}nm_{timestamp}"

    nii_stack.header["descrip"] = descrip[:80]
    nii_binary.header["descrip"] = descrip[:80]

    # speichern
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        nib.save(nii_stack, output_dir / f"{stack_metadata['filename']}.nii.gz")  # type: ignore
        nib.save(nii_binary, output_dir / f"{stack_metadata['filename']}_mask.nii.gz")  # type: ignore
        return True
    except Exception as e:
        show_error(f"Failed to save NIfTI files: {e}")
        return False


def save_as_tiff(
    stack: np.ndarray, metadata: dict, binary_stack: np.ndarray, output_dir: Path
) -> bool:
    """
    Save the image stack and its binary mask as TIFF files.

    Parameters
    ----------
    stack : np.ndarray
        The image stack to be saved.
    metadata : dict
        Metadata associated with the image stack.
    binary_stack : np.ndarray
        The binary mask of the image stack to be saved.
    output_dir : Path
        The directory where the TIFF files will be saved.

    Returns
    -------
    bool
        True if saving was successful, False otherwise.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tiff.TiffWriter(output_dir / f"{metadata['filename']}.tiff") as tif:
            tif.write(stack, photometric="minisblack", metadata=metadata)
        with tiff.TiffWriter(
            output_dir / f"{metadata['filename']}_binary.tiff"
        ) as bin_tif:
            bin_tif.write(binary_stack, photometric="minisblack", metadata=metadata)
        return True
    except Exception as e:
        show_error(f"Failed to save TIFF files: {e}")
        return False


# Functions for saving/loading settings
def save_settings(
    settings_file, user_handle: str, setting_widgets: list, stack_metadata: dict | None
) -> bool:
    settings = {}

    if stack_metadata is None or not isinstance(stack_metadata, dict):
        show_error(
            "Metadata is required for saving settings. Error in metadata format/existence."
        )
        raise ValueError("Metadata is required for saving settings.")

    filename_image = stack_metadata["filename"]
    match = re.search(r"_(\d+)_", filename_image)
    image_id = (
        match.group(1) if match else "unknown"
    )  # Read image ID from filename, e.g. "Mina_0054_Mode3D.oct" -> "0054"

    filename = f"settings_{image_id}_{user_handle}.json"
    settings_file = Path(settings_file) / filename

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

    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=4)
            return True
    except Exception as e:
        show_error(f"Failed to save settings: {e}")
        return False


def load_settings(settings_file: Path) -> dict:
    if not settings_file.exists():
        show_error(f"Settings file does not exist: {settings_file}")
        raise FileNotFoundError(f"Settings file not found: {settings_file}")

    with open(settings_file, "r") as f:
        settings = json.load(f)

    return settings
