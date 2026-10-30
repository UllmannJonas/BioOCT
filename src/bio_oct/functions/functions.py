"""
This contains the raw functions that work with numpy arrays.
For the batch processing pipeline to work, all functions
relevant to the processing, need to obey the <Pipeline-Contract>
Pipeline Contract:
- input
    -> image:
        The image stack data as np.ndarray.
        Can also be a binary image.
        This is stored in napari "image" or "labels" layer.data.
    -> kwargs:
        Any function-specific kwargs.
        E.g. "size" for median filter, "sigma" for gauss filter etc.
- output
    ->  The return value should be a single numpy array of same shape and dtype as input array.
        So if the input image is from a "labels" layer (binary) it should output that format.
"""

from __future__ import annotations

# python native imports
from pathlib import Path
from typing import Literal

import numpy as np

# local imports
from ..shared_utility import THRESHOLD_METHODS
from ._function_helpers import (
    _calc_bv_map,
    _calc_height_map,
    _calc_metrics,
    _convert_to_8bit,
    _get_color_id,
    _is_same_shape,
    _is_uint8,
    _map_coords_to3D,
    _plot_bv_map,
    _plot_height_map,
    _roi_to_volume,
    _save_or_append_metrics,
    _threshold_methods,
    _threshold_values,
    _untilt,
)
from .registry import register, store_roi_metadata


@register(output="image", after=store_roi_metadata)
def define_roi(
    image: np.ndarray,
    roi_corner_points: list[tuple[int, int]] | np.ndarray,
) -> np.ndarray:
    """Define a 3D ROI from four corners in the top-down (xy) view.

    Points are (b_scan, lateral) pairs in voxel indices, defining a
    quadrilateral that is extruded through all axial depths.
    Voxels inside the ROI keep their original values; all outside are set to zero.
    """

    mask3d = _roi_to_volume(roi_corner_points, shape=image.shape)

    roi_image = np.where(mask3d, image, 0).astype(image.dtype)

    return roi_image


@register(output="image")
def median_filter(image: np.ndarray, kernel_size: int = 1) -> np.ndarray:
    import cv2

    _is_uint8(image)

    filtered = np.empty_like(image)
    for b_scan in range(image.shape[0]):
        filtered[b_scan, :, :] = cv2.medianBlur(image[b_scan, :, :], kernel_size)
    return filtered


@register(output="image")
def gaussian_filter(image: np.ndarray, sigma: float = 0.0) -> np.ndarray:
    import cv2

    _is_uint8(image)

    filtered = np.empty_like(image)
    for b_scan in range(image.shape[0]):
        filtered[b_scan, :, :] = cv2.GaussianBlur(
            image[b_scan, :, :], ksize=(0, 0), sigmaX=sigma, sigmaY=sigma
        )
    return filtered


@register(output="image")
def sobel_filter(image: np.ndarray) -> np.ndarray:
    import cv2

    _is_uint8(image)

    magnitude = np.zeros_like(image, dtype=np.float32)
    for b_scan in range(image.shape[0]):
        sobel_axial = cv2.Sobel(
            image[b_scan, :, :], ddepth=cv2.CV_32F, dx=0, dy=1, ksize=3
        )
        magnitude[b_scan, :, :] = np.abs(sobel_axial)

    magnitude = _convert_to_8bit(magnitude)
    return magnitude


@register(output="labels")
def locate_surface(
    image: np.ndarray,
    upper_bound: int,
    lower_bound: int,
    axial_offset: int = 0,
    color_id: int = 1,
) -> np.ndarray:
    ymin = upper_bound
    ymax = lower_bound

    if ymin >= ymax:
        raise ValueError(f"ymin must be less than ymax.\nymin={ymin}\nymax={ymax}")
    if ymin < 0 or ymax > image.shape[1]:
        raise ValueError("Index out of bounds.")

    search = image[:, ymin:ymax, :]
    valid = np.any(search > 0, axis=1)  # Exclude A-scans with no signal in search area

    y_coords = np.argmax(search, axis=1)
    y_coords = y_coords + ymin + axial_offset

    return _map_coords_to3D(y_coords, image.shape, color_id, valid=valid)


@register(output="labels")
def remove_small_objects(labels: np.ndarray, max_object_size: int = 0) -> np.ndarray:
    from skimage import morphology

    color_id = _get_color_id(labels)

    b_scans = labels.shape[0]
    bool_image = labels.astype(bool)
    output = np.empty_like(labels, dtype=bool)

    for bscan in range(b_scans):
        output[bscan, :, :] = morphology.remove_small_objects(
            bool_image[bscan, :, :], max_size=max_object_size, connectivity=2
        )

    output = output.astype(np.uint8) * color_id
    return output


@register(output="labels", context=("roi_corner_points",))
def interpolate_gaps(
    surface: np.ndarray,
    roi_corner_points: list[tuple[int, int]] | np.ndarray | None = None,
) -> np.ndarray:
    from scipy.interpolate import griddata

    color_id = _get_color_id(surface)
    shape_3D = surface.shape

    """
    # ! 2D support, needs testing after v0.4.0
    # 2D case (single B-scan): griddata needs at least 2 points in different positions
    # to triangulate — with shape[0]==1 we only have a 1D problem (lateral axis only),
    # so we use 1D linear interpolation via numpy instead.
    if shape_3D[0] == 1:
        surface_1d = np.argmax(surface[0], axis=0).astype(np.float32)  # (lateral,)
        has_signal = np.any(surface[0] > 0, axis=0)                    # (lateral,)
        gaps = ~has_signal

        if not has_signal.any():
            raise ValueError(
                "No surface points available for interpolation. "
                "Ensure the layer contains coordinate labels inside the ROI."
            )

        if gaps.any():
            x = np.arange(shape_3D[2])
            surface_1d[gaps] = np.interp(x[gaps], x[has_signal], surface_1d[has_signal])

        surface_2D = surface_1d[np.newaxis, :]  # (1, lateral)
        return _map_coords_to3D(surface_2D, shape_3D, color_id, valid=has_signal[np.newaxis, :])
    """

    if roi_corner_points is not None:
        pts = np.asarray(roi_corner_points, dtype=np.int32)
        roi_mask = _roi_to_volume(pts, shape=shape_3D)
        in_roi = np.any(roi_mask, axis=1)  # only include A-scans in ROI
    else:
        in_roi = np.ones((shape_3D[0], shape_3D[2]), dtype=bool)  # include all A-scans

    src_mask = in_roi & np.any(surface > 0, axis=1)  # all points with labels inside roi
    gaps_to_fill = in_roi & ~np.any(
        surface > 0, axis=1
    )  # all points without labels inside roi

    surface_2D = np.argmax(surface, axis=1).astype(np.float32)  # hight coordinates
    surface_2D[~in_roi] = np.nan  # ~ means "not"
    surface_2D[gaps_to_fill] = np.nan

    src_points = np.column_stack(np.where(src_mask))
    values = surface_2D[src_mask]

    if src_points.shape[0] == 0:
        raise ValueError(
            "No surface points available for interpolation. "
            "Ensure the layer contains coordinate labels inside the ROI."
        )

    if not np.any(gaps_to_fill):
        return _map_coords_to3D(surface_2D, shape_3D, color_id, valid=src_mask)

    gap_points = np.column_stack(np.where(gaps_to_fill))
    filled = griddata(src_points, values, gap_points, method="linear")

    if np.isnan(filled).any():
        nearest = griddata(src_points, values, gap_points, method="nearest")
        filled[np.isnan(filled)] = nearest[np.isnan(filled)]

    gap_rows, gap_cols = np.where(gaps_to_fill)
    surface_2D[gap_rows, gap_cols] = filled

    return _map_coords_to3D(surface_2D, shape_3D, color_id, valid=in_roi)


@register(output="image")
def zero_out_area(
    image: np.ndarray, surface_coords: np.ndarray, direction: Literal["above", "below"]
) -> np.ndarray:
    _is_same_shape(image, surface_coords)

    yy = np.arange(image.shape[1])  # Create a range for y-coordinates
    yy = yy.reshape(1, -1, 1)  # Reshape to ensure it can be broadcasted

    surface = np.argmax(surface_coords, axis=1)

    copy = image.copy()

    if direction == "below":
        # Set pixels below and equal to the coords to zero
        copy[yy >= surface[:, np.newaxis, :]] = 0
    elif direction == "above":
        # Set pixels above and equal to the coords to zero
        copy[yy <= surface[:, np.newaxis, :]] = 0

    return copy


@register(output="image")
def replace_reflection(
    image: np.ndarray,
    reflection: np.ndarray,
    axial_padding: int = 1,
    axial_offset: int = 5,
) -> np.ndarray:
    _is_same_shape(image, reflection)

    if (axial_padding * 2 + 1) >= axial_offset:
        raise ValueError(
            "Offset must be at least padding*2 + 1 to avoid overlap of replacement area."
        )

    result = image.copy()

    reflection_surface = np.argmax(reflection, axis=1)

    z_coords, x_coords = np.meshgrid(
        np.arange(image.shape[0]), np.arange(image.shape[2]), indexing="ij"
    )

    for shift in range(-axial_padding, axial_padding + 1):
        source_y = np.clip(
            reflection_surface + axial_offset + shift, 0, image.shape[1] - 1
        )
        target_y = np.clip(reflection_surface + shift, 0, image.shape[1] - 1)
        result[z_coords, target_y, x_coords] = image[z_coords, source_y, x_coords]

    return result


@register(output="image")
def untilt(image: np.ndarray, substratum_coords: np.ndarray | None) -> np.ndarray:
    return _untilt(image, substratum_coords)


@register(output="image")
def enhance_contrast(
    image: np.ndarray,
    method: Literal["gamma", "clip", "clahe"],
    gamma: float = 1.0,
    clip_low_pct: float = 1.0,  # 1%
    clip_high_pct: float = 99.0,  # 99%
    clahe_clip_limit: float = 2.0,
    clahe_tile_size: int = 8,
) -> np.ndarray:
    import cv2

    _is_uint8(image)

    copy = image.copy()
    b_scans = copy.shape[0]

    if method == "gamma":
        # Zero doesnt get scaled so no need to handle it
        # Create LookUpTable for gamma correction
        table = np.array(
            [((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8
        )
        # Apply LUT slice by slice
        for bscan in range(b_scans):
            copy[bscan] = cv2.LUT(copy[bscan], table)

    elif method == "clip":
        # ignore zero values for percentile calc
        hist = np.bincount(image.ravel(), minlength=256)
        hist[0] = 0
        cumulative = np.cumsum(hist)
        total = cumulative[-1]

        low = int(np.searchsorted(cumulative, total * (clip_low_pct / 100.0)))
        high = int(np.searchsorted(cumulative, total * (clip_high_pct / 100.0)))
        if high <= low:
            raise ValueError(
                f"Invalid clip percentiles: low={clip_low_pct}, high={clip_high_pct}. "
                "Ensure that low < high and that the image has sufficient dynamic range."
            )

        lut = (
            np.clip((np.arange(256, dtype=np.float32) - low) / (high - low), 0, 1) * 255
        )
        lut = lut.astype(np.uint8)
        lut[0] = 0

        return lut[image]

    elif method == "clahe":
        clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit, tileGridSize=(clahe_tile_size, clahe_tile_size)
        )
        for bscan in range(b_scans):
            copy[bscan] = clahe.apply(copy[bscan])

    return _convert_to_8bit(copy)


@register(output="labels")
def threshold(
    image: np.ndarray,
    method: str,  # choices set in THRESHOLD_METHODS
    manual_threshold: int = 128,
    ignore_black: bool = True,
    ignore_white: bool = True,
    color_id: int = 9,
) -> np.ndarray:
    if method == "manual":
        t = float(manual_threshold)
        binary = (image > t).astype(np.uint8)
        return binary * color_id

    if method not in THRESHOLD_METHODS:
        raise ValueError(f"Unknown threshold method: {method}")

    values = _threshold_values(image, ignore_black, ignore_white)
    t = float(_threshold_methods()[method](values))
    binary = (image.copy() > t).astype(np.uint8)
    return binary * color_id


@register(output=None)
def export_to_tiff(image: np.ndarray, spacing: np.ndarray, path: Path) -> None:
    import tifffile as tiff

    bscans_spacing = spacing[0] * 1000.0
    lateral_res = 1.0 / (spacing[2] * 1000)
    axial_res = 1.0 / (spacing[1] * 1000)

    dims = 3
    direction = np.eye(3)
    origin = np.zeros(3)
    affine = np.eye(4)
    affine[:dims, :dims] = direction @ np.diag(spacing)
    affine[:dims, dims] = origin

    dir = path.parent
    filename = path.stem

    i = 1
    while path.exists():
        path = dir / f"{filename}_{i}.tiff"
        i += 1

    tiff.imwrite(
        str(path),
        data=image,
        imagej=True,
        resolution=(lateral_res, axial_res),
        metadata={
            "spacing": bscans_spacing,  # for b_scans axis
            "unit": "um",  # for all data
            "affine": affine.tolist(),
        },
    )


@register(output=None)
def export_to_nifti(image: np.ndarray, affine: np.ndarray, path: Path) -> None:
    from medvol import MedVol

    # remove .gz so that path.stem works correctly
    tmp_path = Path(str(path).replace(".gz", ""))

    dir = tmp_path.parent
    filename = tmp_path.stem

    i = 1
    while path.exists():
        path = dir / f"{filename}_{i}.nii.gz"
        i += 1

    nifti = MedVol(image, affine=affine)  # type: ignore
    nifti.save(path)


@register(output=None)
def create_height_map(
    segmentation: np.ndarray,
    substratum: np.ndarray | None = None,
    spacing: np.ndarray | None = None,
    max_height_um: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    preview: bool = False,
    axes: bool = False,
    path: Path | None = None,
) -> None:
    import matplotlib.pyplot as plt

    height_map = _calc_height_map(
        binary=segmentation,
        substratum=substratum,
        axial_spacing=spacing[1] if spacing is not None else None,
    )

    fig = _plot_height_map(
        height_map=height_map,
        spacing=spacing,
        max_h=max_height_um,
        colorbar=colorbar,
        scalebar=scalebar,
        axes=axes,
    )

    if preview:
        fig.set_dpi(300)
        plt.show(block=False)
    else:
        if path is None:
            raise ValueError("path must be provided if preview is not selected.")

        dir = path.parent
        filename = path.stem  # includes _Hmap
        i = 1
        while path.exists():
            path = dir / f"{filename}_{i}.tiff"
            i += 1
        fig.savefig(path, dpi=1200)


@register(output=None)
def create_bv_map(
    segmentation: np.ndarray,
    substratum: np.ndarray | None = None,
    spacing: np.ndarray | None = None,
    max_height_um: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    preview: bool = False,
    axes: bool = False,
    path: Path | None = None,
) -> None:
    import matplotlib.pyplot as plt

    bv_map = _calc_bv_map(
        binary=segmentation,
        substratum=substratum,
        spacing=spacing if spacing is not None else None,
    )

    fig = _plot_bv_map(
        bv_map,
        spacing=spacing,
        max_h=max_height_um,
        colorbar=colorbar,
        scalebar=scalebar,
        axes=axes,
    )

    if preview:
        fig.set_dpi(300)
        plt.show(block=False)
    else:
        if path is None:
            raise ValueError("path must be provided if preview is not selected.")

        dir = path.parent
        filename = path.stem  # includes BVmap
        i = 1
        while path.exists():
            path = dir / f"{filename}_{i}.tiff"
            i += 1
        fig.savefig(path, dpi=1200)


@register(
    output=None,
    context=("layername", "roi_corner_points"),
)
def calculate_metrics(
    segmentation: np.ndarray,
    layername: str,
    path: Path,
    spacing: np.ndarray,
    substratum: np.ndarray | None = None,
    roi_corner_points: list[tuple[int, int]] | np.ndarray | None = None,
) -> None:
    results = _calc_metrics(
        segmentation,
        layername,
        spacing,
        substratum,
        roi_corner_points=roi_corner_points,
    )

    _save_or_append_metrics(results, path)
