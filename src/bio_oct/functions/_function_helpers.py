from __future__ import annotations

from collections.abc import Callable
from functools import cache
from math import isclose
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from ..shared_utility import THRESHOLD_METHODS

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


def _convert_to_8bit(image: np.ndarray) -> np.ndarray:
    lo = float(image.min())
    hi = float(image.max())
    converted = np.zeros(image.shape, dtype=np.uint8)
    if hi == lo:
        return converted

    scale = hi - lo
    for i in range(image.shape[0]):
        tmp = image[i].astype(np.float32)
        tmp -= lo
        tmp /= scale
        tmp *= 255.0
        converted[i] = tmp.astype(np.uint8)

    return converted


def _roi_to_volume(
    points: list[tuple[int, int]] | np.ndarray,
    shape: tuple[int, ...],
) -> np.ndarray:
    import cv2

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
    # Replace NaN with 0 to avoid RuntimeWarning during cast
    coords_clean = np.nan_to_num(coords, nan=0.0)
    axial_idx = np.clip(np.rint(coords_clean), 0, axial - 1).astype(int)

    if valid is None:
        valid = np.ones(coords.shape, dtype=bool)

    mapped[b_scans_idx[valid], axial_idx[valid], lateral_idx[valid]] = label_id

    return mapped


def _visualize_search_area(
    image_shape: tuple[int, ...], ymin: int, ymax: int
) -> np.ndarray:
    area = np.zeros(image_shape, dtype=np.uint8)
    area[:, ymin + 1 : ymax, :] = 1
    return area


def _present_values(a: np.ndarray) -> np.ndarray:
    counts = np.zeros(256, np.int64)
    for b in a:
        counts += np.bincount(b.reshape(-1), minlength=256)
    return np.flatnonzero(counts)


def _is_binary(binary_stack: np.ndarray) -> bool:
    present = _present_values(binary_stack)
    return len(present) <= 2 and present[0] == 0


def _get_color_id(binary_stack: np.ndarray) -> int:
    present = _present_values(binary_stack)
    if not (len(present) <= 2 and present[0] == 0):
        raise ValueError("Input stack is not binary.")

    return int(present[-1])


def _is_same_shape(stackA: np.ndarray, stackB: np.ndarray) -> None:
    if stackA.shape != stackB.shape:
        raise ValueError("Stacks not of same shape.")


def _is_uint8(image: np.ndarray) -> None:
    if image.dtype != np.uint8:
        raise ValueError("Image data-type must be uint8. Use convert widget.")


def _threshold_values(
    image: np.ndarray,
    ignore_black: bool,
    ignore_white: bool,
) -> np.ndarray:
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
    return values


def _calc_thresholds(
    image: np.ndarray,
    methods: list[str],
    manual_value: int = 128,
    ignore_black: bool = True,
    ignore_white: bool = True,
) -> dict[str, float]:
    thresholds = {}

    values = _threshold_values(image, ignore_black, ignore_white)

    for m in methods:
        if m == "manual":
            thresholds[m] = float(manual_value)
        else:
            if m not in THRESHOLD_METHODS:
                raise ValueError(f"Unknown threshold method: {m}")
            thresholds[m] = float(_threshold_methods()[m](values))

    return thresholds


@cache
def _threshold_methods() -> dict[str, Callable[..., Any]]:
    from skimage.filters.thresholding import (
        threshold_isodata,
        threshold_li,
        threshold_mean,
        threshold_otsu,
        threshold_triangle,
        threshold_yen,
    )

    return {
        "otsu": threshold_otsu,
        "yen": threshold_yen,
        "li": threshold_li,
        "mean": threshold_mean,
        "isodata": threshold_isodata,
        "triangle": threshold_triangle,
    }


def _plot_thresholds(
    image: np.ndarray, thresholds: dict[str, float], b_idx: int
) -> None:
    import matplotlib.pyplot as plt

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


def _untilt(image: np.ndarray, substratum_coords: np.ndarray | None) -> np.ndarray:
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


def _calc_height_map(
    binary: np.ndarray,
    substratum: np.ndarray | None = None,
    axial_spacing: float | None = None,
) -> np.ndarray:
    if not _is_binary(binary):
        raise ValueError("Input stack is not binary.")

    untilted = _untilt(binary, substratum)

    hm = np.argmax(untilted, axis=1)
    hm = binary.shape[1] - hm

    # set height indices to 0 where no biofilm signal occurs
    empty_ascans = ~np.any(untilted, axis=1)
    hm[empty_ascans] = 0

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
    import matplotlib.pyplot as plt

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

    untilted = _untilt(binary, substratum)

    bv_map = np.count_nonzero(untilted, axis=1).astype(np.float32)

    if spacing is not None:
        # All spacings in mm; convert to µm for consistent domain
        axial_um = spacing[1] * 1000.0
        bv_map = bv_map * axial_um

    return bv_map


def _plot_bv_map(
    bv_map: np.ndarray,
    spacing: np.ndarray | list[float] | None = None,
    max_h: int | None = None,  # in µm
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
) -> Figure:
    import matplotlib.pyplot as plt

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

    cbar_ylabel = "Thickness (µm)"

    if max_h is None:
        max_h = bv_map.max()

    # Plot with extent and aspect='auto' to maintain correct aspect ratio with physical units
    im = ax.imshow(
        bv_map,
        cmap="inferno",
        vmin=0,
        vmax=max_h,
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
    roi_corner_points: list[tuple[int, int]] | np.ndarray | None = None,
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

    if roi_corner_points is not None:
        pts = np.asarray(roi_corner_points, dtype=np.int32)
        roi_mask = _roi_to_volume(pts, shape=binary.shape)
    else:
        roi_mask = np.ones(binary.shape, dtype=bool)

    roi_mask_2d = np.any(roi_mask, axis=1)
    if not np.any(roi_mask_2d):
        raise ValueError("ROI does not contain any A-scans.")

    lateral_um = spacing[2] * 1000.0
    bscan_um = spacing[0] * 1000.0

    # H-/BV-map independent metrics
    pixel_count = np.sum(binary[roi_mask] != 0)
    # area of one A-scan in µm² = lateral_um * bscan_um
    substratum_area = np.sum(roi_mask_2d) * lateral_um * bscan_um
    # biovolume_dense represents all biofilm-classified pixels condensed, pores removed
    biovolume_dense = np.sum(BVmap[roi_mask_2d]) * lateral_um * bscan_um
    # Porous volume: Hmap is height in µm, multiply by lateral*bscan area to get µm³
    biovolume_porous = np.sum(Hmap[roi_mask_2d]) * lateral_um * bscan_um
    porosity = 1 - (biovolume_dense / biovolume_porous) if biovolume_porous > 0 else 0.0
    # Coverage: fraction of A-scans in ROI that contain biofilm
    biofilm_in_roi = np.any(binary, axis=1) & roi_mask_2d
    substratum_coverage = np.sum(biofilm_in_roi) / np.sum(roi_mask_2d)

    # Hmap based metrics
    min_Hmap = np.min(Hmap[roi_mask_2d])
    max_Hmap = np.max(Hmap[roi_mask_2d])
    mean_Hmap = np.mean(Hmap[roi_mask_2d])
    std_Hmap = np.std(Hmap[roi_mask_2d])
    Ra = np.mean(np.abs(Hmap[roi_mask_2d] - mean_Hmap))  # Mittenrauwert [µm]
    Rq = std_Hmap  # quadratische Rauheit (engl. R_rms=root-mean-squared roughness)
    R_coeff = Ra / mean_Hmap if mean_Hmap != 0 else 0.0

    # for csv with rows: param-name, unit, value
    results = [
        ("file", "-", layername),
        ("px_count", "# px", pixel_count),
        ("axial_spacing", "µm", spacing[1] * 1000),
        (
            "lateral_spacing",
            "µm",
            spacing[2] * 1000
            if isclose(spacing[2], spacing[0], abs_tol=0.00005)
            else "inconsistent",
        ),
        ("substratum_area", "mm²", substratum_area / 1e6),
        ("BV_dense", "mm³", biovolume_dense / 1e9),
        ("BV_porous", "mm³", biovolume_porous / 1e9),
        ("porosity", "(%)", porosity * 100),
        ("substratum_coverage", "(%)", substratum_coverage * 100),
        ("min_height", "µm", min_Hmap),
        ("max_height", "µm", max_Hmap),
        ("mean_height", "µm", mean_Hmap),
        ("std_height", "µm", std_Hmap),
        ("Ra", "µm", Ra),
        ("Rq", "µm", Rq),
        ("R_coeff", "-", R_coeff),
    ]

    return results


def _save_or_append_metrics(results, path: Path) -> None:
    import pandas as pd

    """Save metrics on first call, append on subsequent calls."""
    parameters, units, values = zip(*results)

    columns = pd.MultiIndex.from_tuples(
        list(zip(parameters, units)), names=["parameter", "unit"]
    )

    new_row = pd.DataFrame([values], columns=columns)

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
    from scipy.interpolate import griddata

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
