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

# region IMPORTS
# python native imports
from typing import Literal
from pathlib import Path
import tifffile as tiff

# third party imports
import cv2
from medvol import MedVol
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from scipy.interpolate import griddata
from skimage import morphology

# local imports
from .registry import register
from .constants import Fn, THRESHOLD_METHODS

# endregion IMPORTS


# -----------------------------------------------------------------------
# --- Processing functions --------------------------------------------------
# region FUNCTIONS
@register("define_roi")
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


@register(Fn.MEDIAN_FILTER)
def median_filter(image: np.ndarray, kernel_size: int = 1) -> np.ndarray:
    _is_uint8(image)

    filtered = np.empty_like(image)
    for b_scan in range(image.shape[0]):
        filtered[b_scan, :, :] = cv2.medianBlur(image[b_scan, :, :], kernel_size)
    return filtered


@register("gaussian_filter")
def gaussian_filter(image: np.ndarray, sigma: float = 0.0) -> np.ndarray:
    _is_uint8(image)

    filtered = np.empty_like(image)
    for b_scan in range(image.shape[0]):
        filtered[b_scan, :, :] = cv2.GaussianBlur(
            image[b_scan, :, :], ksize=(0, 0), sigmaX=sigma, sigmaY=sigma
        )
    return filtered


@register("sobel_filter")
def sobel_filter(image: np.ndarray) -> np.ndarray:
    _is_uint8(image)

    magnitude = np.zeros_like(image, dtype=np.float32)
    for b_scan in range(image.shape[0]):
        sobel_axial = cv2.Sobel(
            image[b_scan, :, :], ddepth=cv2.CV_32F, dx=0, dy=1, ksize=3
        )
        magnitude[b_scan, :, :] = np.abs(sobel_axial)

    magnitude = _convert_to_8bit(magnitude)
    return magnitude


@register("locate_surface")
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
    valid = np.any(image > 0, axis=1)  # Exclude A-scans with only zeros (roi masked)

    y_coords = np.argmax(search, axis=1)
    y_coords = y_coords + ymin + axial_offset

    return _map_coords_to3D(y_coords, image.shape, color_id, valid=valid)


@register("remove_small_objects")
def remove_small_objects(labels: np.ndarray, max_object_size: int = 0) -> np.ndarray:
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


@register("interpolate_gaps")
def interpolate_gaps(
    surface: np.ndarray,
    roi_corner_points: list[tuple[int, int]] | np.ndarray | None = None,
) -> np.ndarray:
    color_id = _get_color_id(surface)
    shape_3D = surface.shape

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


@register("zero_out_area")
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


@register("replace_reflection")
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


@register("untilt")
def untilt(image: np.ndarray, substratum_coords: np.ndarray | None) -> np.ndarray:
    if substratum_coords is None:
        return image

    _is_same_shape(image, substratum_coords)

    coords = np.argmax(substratum_coords, axis=1)
    bscans, axial, lateral = image.shape
    untilted = np.zeros_like(image)

    for bscan in range(bscans):
        for ascan in range(lateral):
            y_sub = coords[bscan, ascan]
            untilted[bscan, (axial - y_sub) : axial, ascan] = image[
                bscan, 0:y_sub, ascan
            ]

    return untilted


@register("enhance_contrast")
def enhance_contrast(
    image: np.ndarray,
    method: Literal["gamma", "clip", "clahe"],
    gamma: float = 1.0,
    clip_low_pct: float = 1.0,  # 1%
    clip_high_pct: float = 99.0,  # 99%
    clahe_clip_limit: float = 2.0,
    clahe_tile_size: int = 8,
) -> np.ndarray:
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
        mask = copy > 0
        non_zero = copy[mask]
        low = np.percentile(non_zero, clip_low_pct)
        high = np.percentile(non_zero, clip_high_pct)
        copy = np.clip(copy, low, high)
        copy = (copy - low) / (high - low) * 255  # rescale to full range
        copy[~mask] = 0  # set zero values back to zero after clipping

    elif method == "clahe":
        clahe = cv2.createCLAHE(
            clipLimit=clahe_clip_limit, tileGridSize=(clahe_tile_size, clahe_tile_size)
        )
        for bscan in range(b_scans):
            copy[bscan] = clahe.apply(copy[bscan])

    return _convert_to_8bit(copy)


@register("threshold")
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

    # ignore black/white pixels as selected
    values = image.flatten()
    if ignore_black:
        values = values[values > 0]
    if ignore_white:
        if image.dtype == np.uint8:
            values = values[values < 255]
        elif image.dtype == np.float32:
            values = values[values < 1.0]
        else:
            raise ValueError(f"Unsupported image dtype ({image.dtype}).")

    # calc threshold
    t = float(THRESHOLD_METHODS[method](values))
    binary = (image.copy() > t).astype(np.uint8)
    return binary * color_id


@register("export_to_tiff")
def export_to_tiff(image: np.ndarray, spacing: np.ndarray, path: Path) -> None:
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


@register("export_to_nifti")
def export_to_nifti(image: np.ndarray, affine: np.ndarray, path: Path) -> None:
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


@register("create_height_map")
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


@register("create_bv_map")
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


@register("calculate_metrics")
def calculate_metrics(
    segmentation: np.ndarray,
    layername: str,
    path: Path,
    spacing: np.ndarray,
    substratum: np.ndarray | None = None,
) -> None:
    results = _calc_metrics(segmentation, layername, spacing, substratum)

    _save_or_append_metrics(results, path)


# endregion FUNCTIONS


# -----------------------------------------------------------------------
# --- Helper functions --------------------------------------------------
# region HELPERS
def _convert_to_8bit(image: np.ndarray) -> np.ndarray:
    image = (image - image.min()) / (image.max() - image.min())

    converted = (image * 255).astype(np.uint8)
    return converted


def _roi_to_volume(
    points: list[tuple[int, int]] | np.ndarray,
    shape: tuple[int, ...],
) -> np.ndarray:
    points = np.asarray(points, dtype=np.int32)
    if points.shape != (4, 2):
        raise ValueError(
            f"Expected exactly 4 (u, v) coordinate pairs, got shape {points.shape}."
        )

    cv_points = np.stack([points[:, 1], points[:, 0]], axis=1).reshape((-1, 1, 2))

    roi2d = np.zeros((shape[0], shape[2]), dtype=np.uint8)
    cv2.fillPoly(roi2d, [cv_points], 1)
    roi2d = roi2d.astype(bool)
    extruded = np.broadcast_to(roi2d[:, np.newaxis, :], shape).copy()

    return extruded


def _map_coords_to3D(
    coords: np.ndarray,
    image_shape: tuple[int, int, int],
    label_id: int = 1,
    valid: np.ndarray | None = None,
) -> np.ndarray:
    mapped = np.zeros(image_shape, dtype=np.uint8)
    b_scans, axial, lateral = image_shape

    b_scans_idx, lateral_idx = np.meshgrid(
        np.arange(b_scans), np.arange(lateral), indexing="ij"
    )
    axial_idx = np.clip(np.rint(coords), 0, axial - 1).astype(int)

    if valid is None:
        valid = np.ones(coords.shape, dtype=bool)

    mapped[b_scans_idx[valid], axial_idx[valid], lateral_idx[valid]] = label_id

    return mapped


def _vizualize_search_area(
    image_shape: tuple[int, ...], ymin: int, ymax: int
) -> np.ndarray:
    area = np.zeros(image_shape, dtype=np.uint8)
    area[:, ymin + 1 : ymax, :] = 1
    return area


def _is_binary(binary_stack: np.ndarray) -> bool:
    unique_vals = np.unique(binary_stack, sorted=True).tolist()
    if not unique_vals[0] == 0 or len(unique_vals) > 2:
        return False

    return True


def _get_color_id(binary_stack: np.ndarray) -> int:
    if not _is_binary(binary_stack):
        raise ValueError("input stack is not binary.")

    return int(np.unique(binary_stack)[-1])


def _is_same_shape(stackA: np.ndarray, stackB: np.ndarray) -> None:
    if stackA.shape != stackB.shape:
        raise ValueError("Stacks not of same shape.")


def _is_uint8(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError("Image data-type must be uint8. Use convert widget.")


def _calc_thresholds(
    image: np.ndarray,
    methods: list[str],
    manual_value: int = 128,
    ignore_black: bool = True,
    ignore_white: bool = True,
) -> dict[str, float]:
    thresholds = {}

    # ignore black/white pixels as selected
    values = image.flatten()
    if ignore_black:
        values = values[values > 0]
    if ignore_white:
        if image.dtype == np.uint8:
            values = values[values < 255]
        elif image.dtype == np.float32:
            values = values[values < 1.0]
        else:
            raise ValueError(f"Unsupported image dtype ({image.dtype}).")
    elif ignore_black and ignore_white:
        if image.dtype == np.uint8:
            values = values[(values > 0) & (values < 255)]
        elif image.dtype == np.float32:
            values = values[(values > 0.0) & (values < 1.0)]
        else:
            raise ValueError(f"Unsupported image dtype ({image.dtype}).")

    for m in methods:
        if m == "manual":
            thresholds[m] = float(manual_value)
        else:
            if m not in THRESHOLD_METHODS:
                raise ValueError(f"Unknown threshold method: {m}")
            thresholds[m] = float(THRESHOLD_METHODS[m](values))

    return thresholds


def _plot_thresholds(
    image: np.ndarray, thresholds: dict[str, float], b_idx: int
) -> None:
    n = len(thresholds)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), squeeze=False)
    axes = axes[0]
    for ax, (name, t) in zip(axes, thresholds.items()):
        mask = image > t
        ax.imshow(image, cmap="gray", aspect="auto")
        ax.imshow(mask, cmap="viridis", alpha=0.3, aspect="auto")
        ax.set_title(f"{name}  (t={round(t)})")
        ax.axis("off")
    fig.suptitle(f"B-Scan {b_idx} — threshold preview")
    plt.tight_layout()
    plt.show(block=False)


def _calc_height_map(
    binary: np.ndarray,
    substratum: np.ndarray | None = None,
    axial_spacing: float | None = None,
) -> np.ndarray:
    if not _is_binary(binary):
        raise ValueError("Input stack is not binary.")

    untilted = untilt(binary, substratum)

    hm = np.argmax(np.flip(untilted, axis=1), axis=1)
    # set height indices to 0 where no biofilm signal occurs
    hm[~np.any(binary, axis=1)] = 0

    # Convert index to physical height
    if axial_spacing is not None:
        hm = hm.astype(np.float32) * (axial_spacing * 1000.0)

    return hm


def _plot_height_map(
    height_map: np.ndarray,
    spacing: np.ndarray | list[float] | None = None,
    max_h: int | None = None,  # in um
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
) -> Figure:
    fig, ax = plt.subplots(constrained_layout=True)
    fig.set_dpi(1200)

    # Calculate extent for physical units
    if spacing is not None:
        # spacing format: [bscans, axial, lateral] in mm
        extent = (  # [left, right, bottom, top]
            0.0,
            float(height_map.shape[1] * spacing[2] * 1000),  # lateral
            float(height_map.shape[0] * spacing[0] * 1000),  # bscans
            0.0,
        )
    else:
        extent = None

    # Set vmax
    vmax = max_h if max_h is not None else height_map.max()  # already in um

    # Plot with extent and aspect='auto' to maintain correct aspect ratio with physical units
    im = ax.imshow(
        height_map,
        cmap="inferno",
        vmin=0,
        vmax=vmax,
        extent=extent,
        aspect="equal",
        interpolation="nearest",
    )

    if axes and spacing is not None:
        ax.set_xlabel("Lateral (µm)")
        ax.set_ylabel("B-scans (µm)")

    if colorbar:
        cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.ax.set_ylabel("Height (µm)", rotation=270, labelpad=15)

    if scalebar and spacing is not None:
        assert extent is not None, "Extent must be calculated for scalebar."
        _create_horizontal_scale_bar(extent, ax)

    return fig


def _calc_bv_map(
    binary: np.ndarray,
    substratum: np.ndarray | None = None,
    spacing: np.ndarray | list[float] | None = None,
) -> np.ndarray:
    if not _is_binary(binary):
        raise ValueError("Input stack is not binary.")

    untilted = untilt(binary, substratum)

    bv_map = np.count_nonzero(untilted, axis=1).astype(np.float32)

    if spacing is not None:
        bv_map = bv_map * (spacing[1] * 1000.0)  # gives "dense" height in µm
        area = spacing[0] * spacing[2] * 1000000.0  # mm² to µm²
        bv_map = bv_map * area  # convert to biovolume in µm³

    return bv_map


def _plot_bv_map(
    bv_map: np.ndarray,
    spacing: np.ndarray | list[float] | None = None,
    max_h: int | None = None,  # in µm
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
) -> Figure:
    fig, ax = plt.subplots(constrained_layout=True)
    fig.set_dpi(1200)

    # Calculate extent for physical units
    if spacing is not None:
        # spacing format: [bscans, axial, lateral] in mm
        extent = (  # [left, right, bottom, top]
            0.0,
            float(bv_map.shape[1] * spacing[2] * 1000),  # lateral
            float(bv_map.shape[0] * spacing[0] * 1000),  # bscans
            0.0,
        )
    else:
        extent = None

    # Set vmax
    if spacing is not None:
        spacing_bscans = spacing[0] * 1000.0
        spacing_lateral = spacing[2] * 1000.0
        cbar_ylabel = "Volume (µm³)"
    else:
        spacing_bscans = 1.0
        spacing_lateral = 1.0
        cbar_ylabel = "Thickness (µm)"

    if max_h is not None:
        max_vol = max_h * spacing_lateral * spacing_bscans
    else:
        max_vol = bv_map.max() * spacing_bscans * spacing_lateral

    # Plot with extent and aspect='auto' to maintain correct aspect ratio with physical units
    im = ax.imshow(
        bv_map,
        cmap="inferno",
        vmin=0,
        vmax=max_vol,
        extent=extent,
        aspect="equal",
        interpolation="nearest",
    )

    if axes and spacing is not None:
        ax.set_xlabel("Lateral (µm)")
        ax.set_ylabel("B-scans (µm)")

    if colorbar:
        cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.ax.set_ylabel(cbar_ylabel, rotation=270, labelpad=15)

    if scalebar and spacing is not None:
        assert extent is not None, "Extent must be calculated for scalebar."
        _create_horizontal_scale_bar(extent, ax)

    return fig


def _create_horizontal_scale_bar(
    extent: tuple[float, float, float, float], ax: Axes
) -> None:
    """Add a horizontal scale bar (1 mm) to the plot.

    Args:
        extent: The extent tuple [left, right, bottom, top] in µm from imshow
        ax: matplotlib axes
    """
    left, right, bottom, top = extent

    scale_bar_um = 1000.0  # 1 mm in µm

    # Positioning parameters (as fraction of extent)
    margin_fraction = 0.05
    margin_right = (right - left) * margin_fraction
    margin_bottom = (bottom - top) * (margin_fraction * 0.5)

    # Scalebar endpoints (positioned at bottom-right)
    scalebar_x_end = right - margin_right
    scalebar_x_start = scalebar_x_end - scale_bar_um
    scalebar_y = bottom - margin_bottom

    # Draw the scalebar line
    ax.plot(
        [scalebar_x_start, scalebar_x_end],
        [scalebar_y, scalebar_y],
        color="white",
        lw=2,
        zorder=10,
    )

    # Add text label
    text_x = (scalebar_x_start + scalebar_x_end) / 2
    text_y_offset = (bottom - top) * 0.01
    text_y = scalebar_y - text_y_offset
    ax.text(
        text_x,
        text_y,
        "1 mm",
        color="white",
        fontsize=10,
        ha="center",
        va="bottom",
    )


def _calc_metrics(
    binary: np.ndarray,
    layername: str,
    spacing: np.ndarray,
    substratum: np.ndarray | None = None,
) -> list[tuple]:
    if not _is_binary(binary):
        raise ValueError("Input image not binary.")

    Hmap = _calc_height_map(
        binary,
        substratum,
        spacing[1],
    )
    BVmap = _calc_bv_map(
        binary,
        substratum,
        spacing,
    )

    bscans, _, lateral = binary.shape
    spacing_factor = spacing[0] * spacing[2] * 1000000.0  # mm² to µm²
    valid = Hmap > 0

    # H-/BV-map independent metrics
    pixel_count = np.sum(binary != 0)
    substratum_area = bscans * lateral * spacing_factor
    biovolume_dense = np.sum(BVmap)
    biovolume_porous = np.sum(Hmap) * spacing_factor
    porosity = 1 - (biovolume_dense / biovolume_porous)  # percentage value [0, 1]
    substratum_coverage = np.sum(valid) / (bscans * lateral)  # percentage value [0, 1]

    #! question: use valid or not -> how does it influence real world properties if left out?
    # Hmap based metrics
    min_Hmap = np.min(Hmap[valid])
    max_Hmap = np.max(Hmap[valid])
    mean_Hmap = np.mean(Hmap[valid])
    std_Hmap = np.std(Hmap[valid])
    Ra = np.mean(np.abs(Hmap[valid] - mean_Hmap))  # Mittenrauwert [µm]
    Rq = std_Hmap  # quadratische Rauheit (engl. R_rms=root-mean-squared roughness)
    R_coeff = Ra / np.mean(Hmap)  # Roughness coefficient for flow calculations

    # BVmap based metrics
    # mean_local_volume = np.mean(BVmap[valid])
    # std_local_volume = np.std(BVmap[valid])

    # for csv with rows: param-name, unit, value
    results = [
        ("file", "-", layername),
        ("px_count", "# px", pixel_count),
        ("substratum_area", "µm²", substratum_area),
        ("BV_dense", "µm³", biovolume_dense),
        ("BV_porous", "µm³", biovolume_porous),
        ("porosity", "(%)", porosity),
        ("substratum_coverage", "(%)", substratum_coverage),
        ("min_height", "µm", min_Hmap),
        ("max_height", "µm", max_Hmap),
        ("mean_height", "µm", mean_Hmap),
        ("std_height", "µm", std_Hmap),
        ("Ra", "µm", Ra),
        ("Rq", "µm", Rq),
        ("R_coeff", "-", R_coeff),
        # ("mean_local_volume", "µm³", mean_local_volume),
        # ("std_local_volume", "µm³", std_local_volume),
    ]

    return results


def _save_or_append_metrics(results, path: Path) -> None:
    """Save metrics on first call, append on subsequent calls."""
    parameters, units, values = zip(*results)

    columns = pd.MultiIndex.from_tuples(
        list(zip(parameters, units)), names=["parameter", "unit"]
    )

    new_row = pd.DataFrame([values], columns=columns)
    new_row = new_row.round(
        {(parameter, unit): 4 if unit == "(%)" else 1 for parameter, unit, _ in results}
    )

    if path.exists():
        df_existing = pd.read_csv(
            path,
            sep=";",
            decimal=",",
            encoding="utf-8-sig",
            header=[0, 1],  # parameters and units rows
        )

        if list(df_existing.columns) != list(columns):
            raise ValueError(
                f"Metric columns do not match existing csv data.\nExisting: {list(df_existing.columns)}\nNew: {list(columns)}"
            )

        df_final = pd.concat([df_existing, new_row], ignore_index=True)
    else:
        df_final = new_row

    df_final.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")


def _reconstruct_substratum(binary_image: np.ndarray) -> np.ndarray:
    """Finds the substratum in a binary image by retrieving the lowest non-zero pixel"""
    if not _is_binary(binary_image):
        raise ValueError("Input image is not binary")

    flipped = np.flip(binary_image, axis=1)  # flip along axial (=axis 1)
    substratum_flipped = np.argmax(flipped, axis=1)

    substratum = binary_image.shape[1] - 1 - substratum_flipped

    # interpolate where substratum_flipped==0, indicating no non-zero value in that a-scan
    substratum_interp = substratum.astype(np.float32)
    gaps = substratum_flipped == 0
    substratum_interp[gaps] = np.nan
    valid = ~np.isnan(substratum_interp)

    Z, X = np.indices(substratum_interp.shape)
    points = np.column_stack((Z[valid], X[valid]))
    values = substratum_interp[valid]

    interpolated = griddata(points, values, (Z, X), method="linear")

    if np.isnan(interpolated).any():
        nearest = griddata(points, values, (Z, X), method="nearest")
        interpolated[np.isnan(interpolated)] = nearest[np.isnan(interpolated)]

    substratum = np.clip(np.rint(interpolated), 0, binary_image.shape[1] - 1).astype(
        np.uint8
    )

    return substratum


# endregion HELPERS
