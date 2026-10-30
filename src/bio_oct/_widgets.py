"""Napari widget facade for the BioOCT plugin.

This module imports widget classes and factory callables that are
registered in the napari manifest. The goal is to keep the manifest entry points
centralized.
"""

# ruff: noqa: F401

from .widgets._dev import expand_coords, print_metadata, set_spacing_widget
from .widgets.define_roi import DefineRoiWidget
from .widgets.enhance_contrast import enhance_contrast_widget
from .widgets.exports import export_to_nifti_widget, export_to_tiff_widget
from .widgets.filters import (
    gaussian_filter_widget,
    median_filter_widget,
    remove_small_objects_widget,
    sobel_filter_widget,
)
from .widgets.isolate import replace_reflection_widget, zero_out_area_widget
from .widgets.locate_surface import (
    LocateSurfaceWidget,
    interpolate_gaps_widget,
)
from .widgets.metrics import (
    calculate_metrics_widget,
    create_bv_map_widget,
    create_height_map_widget,
)
from .widgets.threshold import ThresholdWidget
from .widgets.visualize import untilt_widget
