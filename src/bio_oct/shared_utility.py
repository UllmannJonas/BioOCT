from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import napari.layers


# Constants
COLORMAP: dict[str, int] = {
    "Cyan": 2,
    "Yellow": 9,
    "Red": 10,
    "Blue": 34,
    "Green": 37,
    "Purple": 45,
}

THRESHOLD_METHODS = ("otsu", "yen", "li", "mean", "isodata", "triangle", "manual")


# Output Path
def resolve_output_path(
    filename: str,
    layer: Any,
    output_folder: Path | None = None,
) -> Path:
    """Resolve the output path from a filename template using the layername and output directory.

    Parameters
    ----------
    filename : str
        A filename template. The placeholder ``{input_layer}`` is replaced with
        the source layer name so exported files keep a meaningful label.
    layer : Any
        A napari layer exposing a ``name`` and optional
        ``metadata``.
    output_folder : Path | None, optional
        Directory to write into. When omitted, the layer's ``source_dir`` metadata
        is used and falls back to the user's home directory.

    Returns
    -------
    Path
        The resolved file path, including the destination directory and the
        generated filename.
    """
    metadata = getattr(layer, "metadata", {})
    destination = (
        Path(output_folder)
        if output_folder is not None
        else Path(metadata.get("source_dir", Path.home()))
    )
    layer_name = layer.name if hasattr(layer, "name") else "unknown_layer"
    return destination / filename.replace("{input_layer}", layer_name)


# Naming
"""Suffixes used to generate output layer names for derived data.
If suffixes change, pipeline-versioning must be introduced
since old pipelines will break on replay.
"""
OUTPUT_LAYER_SUFFIXES = (
    "median",
    "gauss",
    "sobel",
    "enhanced",
    "cleaned",
    "interpolated",
    "zeroed",
    "reflection_removed",
    "untilted",
    "roi",
    "binary",
    "surface-coords",
)


def derive_name(input_name: str, suffix: str) -> str:
    """Return a deterministic output name for a derived layer.

    Parameters
    ----------
    input_name : str
        The name of the input layer.
    suffix : str
        The suffix to append to the layer name.

    The helper avoids duplicating a suffix when a layer already carries the same
    processing label, which keeps downstream names stable across repeated
    operations.
    """
    if input_name.endswith(f"_{suffix}"):
        return input_name
    return f"{input_name}_{suffix}"


# Layer Properties
def copy_layer_properties(
    layer: "napari.layers.Layer",
    *,
    include_opacity: bool = False,
    include_contrast_limit: bool = True,
) -> dict[str, Any]:
    """Clone the metadata and display properties that should be preserved.

    Parameters
    ----------
    layer : napari.layers.Layer
        The source layer to copy properties from.
    include_opacity : bool, optional
        Whether to include the layer's opacity in the copied properties.
    include_contrast_limit : bool, optional
        Whether to include the layer's contrast limits in the copied properties.

    This is used when creating derived layers that should keep the original image
    geometry, metadata, and display calibration while still allowing the
    call site to override a few visual defaults.
    """
    properties = {
        "metadata": dict(layer.metadata) if hasattr(layer, "metadata") else {},
        "affine": (layer.affine.affine_matrix if hasattr(layer, "affine") else None),
        "axis_labels": layer.axis_labels if hasattr(layer, "axis_labels") else None,
        "units": layer.units if hasattr(layer, "units") else None,
    }
    if include_opacity and hasattr(layer, "opacity"):
        properties["opacity"] = layer.opacity
    if include_contrast_limit:
        properties["contrast_limits"] = (0, 255)
    return properties


# Tooltips
TOOLTIPS: dict[str, dict[str, str]] = {
    "median": {
        "_widget": "Apply a 2D median filter to each B-scan to reduce noise while preserving edges.",
    },
    "gaussian": {
        "_widget": "Apply a Gaussian blur to reduce gaussian noise.",
    },
    "sobel": {
        "_widget": "Compute axial image gradient (Sobel) to highlight lateral edges.",
        "image": "Input image layer to process.",
    },
    "remove_outliers": {
        "_widget": "Remove connected components from a label image based on size threshold.",
    },
    "interpolate": {
        "_widget": "Interpolate gaps in located intensity coordinates.",
    },
    "zero_out": {
        "_widget": "Zero out (mask) areas above or below the labeled substratum.",
    },
    "replace_reflection": {
        "_widget": "Replace lateral reflection artifacts using nearby image context.",
    },
    "untilt_widget": {
        "_widget": "Axially move substratum to bottom of the image.",
    },
    "export_to_tiff": {
        "_widget": "Export the given layer to a TIFF (.tiff) file in the source directory.",
        "image": "Layer to export.",
    },
    "export_to_nifti": {
        "_widget": "Export the given layer to a NIfTI (.nii.gz) file in the source directory.",
    },
    "h_map": {
        "_widget": "Create a height map (preview or save) from a binary label image.",
    },
    "bv_map": {
        "_widget": "Create a biovolume map from a binary label image.",
    },
    "save_metrics": {
        "_widget": "Calculate biofilm metrics based on a binary label image and save to CSV (.csv).",
    },
}
