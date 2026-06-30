# region IMPORTS
# Python native imports
from typing import Literal, cast, TYPE_CHECKING
from pathlib import Path
import json

# Third party imports
from magicgui import magic_factory
import numpy as np
from numpy import asarray
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSpinBox,
    QComboBox,
    QPushButton,
    QLabel,
    QCheckBox,
    QGroupBox,
)

# Local imports
from . import functions as fn
from .functions import THRESHOLD_METHODS
from .recorder import recorder
from .panel import get_panel
from .constants import (
    Fn,
    SOURCE_DIR_PLACEHOLDER,
    LAYER_NAME_PLACEHOLDER,
    TOOLTIPS,
    COLORMAP,
)

if TYPE_CHECKING:
    import napari.layers
    import napari.types
    import napari.viewer
# endregion IMPORTS


# region WIDGETS
@magic_factory(
    call_button="Apply Median Filter",
    kernel_size={
        "min": 1,
        "step": 2,
        "max": 13,
        "tooltip": TOOLTIPS["median"]["size"],
        "label": "Kernel Size",
    },
    image={"label": "Image"},
)
def median_filter_widget(
    image: "napari.layers.Image", kernel_size: int = 1
) -> "napari.types.LayerDataTuple":
    """
    Apply a 2D median filter to each B-Scan of the selected image.
    A median filter replaces each pixel with the median value of its neighborhood.
    The 'size' parameter determines the size of the neighborhood (must be odd so it has a single center pixel).
    Median filters are effective at removing noise while preserving edges.
    """
    data = fn.median_filter(asarray(image.data), kernel_size)

    if "median" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_median"

    # Recording
    recorder.record(
        function=Fn.MEDIAN_FILTER,
        input_layers={"image": image.name},
        output_layer=output_name,
        params={"kernel_size": kernel_size},
    )
    p = get_panel()
    if p is not None:
        p.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        "contrast_limits": (0, 255) if data.dtype == np.uint8 else (0, 1),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


@magic_factory(
    call_button="Apply Gaussian Filter",
    sigma={"max": 20.0, "tooltip": TOOLTIPS["gaussian"]["sigma"], "label": "Sigma"},
    image={"label": "Image"},
)
def gaussian_filter_widget(
    image: "napari.layers.Image", sigma: float = 0.0
) -> "napari.types.LayerDataTuple":
    data = fn.gaussian_filter(asarray(image.data), sigma)

    if "gauss" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_gauss"

    recorder.record(
        function="gaussian_filter",
        input_layers={"image": image.name},
        output_layer=output_name,
        params={"sigma": sigma},
    )
    p = get_panel()
    if p is not None:
        p.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        "contrast_limits": (0, 255) if data.dtype == np.uint8 else (0, 1),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


@magic_factory(
    call_button="Apply Sobel Filter",
    image={"label": "Image"},
)
def sobel_filter_widget(
    image: "napari.layers.Image",
) -> "napari.types.LayerDataTuple":
    data = fn.sobel_filter(asarray(image.data))

    if "sobel" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_sobel"

    recorder.record(
        function="sobel_filter",
        input_layers={"image": image.name},
        output_layer=output_name,
        params={},
    )
    p = get_panel()
    if p is not None:
        p.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        "contrast_limits": (0, 255) if data.dtype == np.uint8 else (0, 1),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


class LocateSurfaceWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer

        # --- Image Layer Selector ---
        self.image_label = QLabel("Image:")
        self.image_combo = QComboBox()
        self.image_combo.setMinimumWidth(160)
        self.image_combo.addItem("None")
        self._refresh_image_combo()

        image_row = QHBoxLayout()
        image_row.addWidget(self.image_label)
        image_row.addWidget(self.image_combo, stretch=1)

        # --- ymin ---
        self.ymin_label = QLabel("Upper Bound:")
        self.ymin_spin = QSpinBox()

        ymin_row = QHBoxLayout()
        ymin_row.addWidget(self.ymin_label)
        ymin_row.addWidget(self.ymin_spin)

        # --- ymax ---
        self.ymax_label = QLabel("Lower Bound:")
        self.ymax_spin = QSpinBox()

        ymax_row = QHBoxLayout()
        ymax_row.addWidget(self.ymax_label)
        ymax_row.addWidget(self.ymax_spin)

        # --- axial_offset ---
        self.offset_label = QLabel("Axial Offset:")
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-500, 500)
        self.offset_spin.setValue(0)

        offset_row = QHBoxLayout()
        offset_row.addWidget(self.offset_label)
        offset_row.addWidget(self.offset_spin)

        # --- Color ---
        self.color_label = QLabel("Set Color:")
        self.color_combo = QComboBox()
        for name in COLORMAP:
            self.color_combo.addItem(name)
        self.color_combo.setCurrentText("Cyan")

        color_row = QHBoxLayout()
        color_row.addWidget(self.color_label)
        color_row.addWidget(self.color_combo)

        # --- Search Button ---
        self.search_btn = QPushButton("Search")

        # --- Layout ---
        layout = QVBoxLayout()
        layout.addLayout(image_row)
        layout.addLayout(ymin_row)
        layout.addLayout(ymax_row)
        layout.addLayout(offset_row)
        layout.addLayout(color_row)
        layout.addWidget(self.search_btn)
        layout.addStretch()
        self.setLayout(layout)

        # --- Signals ---
        viewer.layers.events.inserted.connect(self._refresh_image_combo)
        viewer.layers.events.removed.connect(self._refresh_image_combo)

        self.image_combo.currentTextChanged.connect(self._on_image_changed)

        self.ymin_spin.valueChanged.connect(self._update_search_window)
        self.ymax_spin.valueChanged.connect(self._update_search_window)
        self.search_btn.clicked.connect(self._on_search)

    def _refresh_image_combo(self, _event=None):
        """Put all current viewer layer names in Dropdown Menu."""
        current = self.image_combo.currentText()
        self.image_combo.blockSignals(True)
        self.image_combo.clear()
        self.image_combo.addItem("None")
        for layer in self.viewer.layers:
            if isinstance(layer, _get_napari_image_class()):
                self.image_combo.addItem(layer.name)
        idx = self.image_combo.findText(
            current
        )  # returns -1 if current doesnt exist (was deleted)
        if idx >= 0:
            self.image_combo.setCurrentIndex(idx)
        else:
            self.image_combo.setCurrentIndex(0)
        self.image_combo.blockSignals(False)

    def _on_image_changed(self, _=None):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        axial_max = image_layer.data.shape[1] - 1

        self.ymin_spin.setMaximum(axial_max - 1)
        self.ymax_spin.setMaximum(axial_max)
        self.ymin_spin.setValue(0)
        self.ymax_spin.setValue(axial_max)
        self._update_search_window()

    def _update_search_window(self, _=None):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        shape = image_layer.data.shape
        axial = shape[1]
        ymin = int(self.ymin_spin.value())
        ymax = int(self.ymax_spin.value())

        ymin = max(0, min(ymin, axial - 2))
        ymax = max(ymin + 1, min(ymax, axial - 1))

        search_area = fn._vizualize_search_area(shape, ymin, ymax)

        existing = [lay.name for lay in self.viewer.layers]
        if "_search_window" in existing:
            lay = self.viewer.layers["_search_window"]
            lay.data = search_area
            lay.refresh()
        else:
            lay = self.viewer.add_labels(
                search_area,
                name="_search_window",
                affine=image_layer.affine.affine_matrix,
                scale=image_layer.scale,
                opacity=0.3,
            )

    def _on_search(self):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        upper_bound = int(self.ymin_spin.value())
        lower_bound = int(self.ymax_spin.value())
        axial_offset = int(self.offset_spin.value())

        label_color = self.color_combo.currentText()
        color_id = COLORMAP[label_color]

        coords = fn.locate_surface(
            asarray(image_layer.data), upper_bound, lower_bound, axial_offset, color_id
        )

        output_name = f"{image_layer.name}_surface-coords"

        existing = [lay.name for lay in self.viewer.layers]
        if output_name in existing:
            lay = self.viewer.layers[output_name]
            lay.data = coords
            lay.refresh()
        else:
            lay = self.viewer.add_labels(
                coords,
                affine=image_layer.affine.affine_matrix,
                name=output_name,
                opacity=1.0,
                metadata={**image_layer.metadata},
                scale=image_layer.scale,
                axis_labels=image_layer.axis_labels,
                units=image_layer.units,
            )

        # --- record ---
        record_params = {
            "upper_bound": upper_bound,
            "lower_bound": lower_bound,
            "axial_offset": axial_offset,
        }
        recorder.record(
            function="locate_surface",
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params=record_params,
        )
        panel = get_panel()
        if panel is not None:
            panel.refresh()

    ## --- Helpers ---
    def _get_selected_image_layer(self):
        name = self.image_combo.currentText()
        if not name:
            return None
        try:
            layer = self.viewer.layers[name]
            return layer if isinstance(layer, _get_napari_image_class()) else None
        except KeyError:
            return None


class DefineRoiWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer

        self.image_label = QLabel("Image:")
        self.image_combo = QComboBox()
        self.image_combo.setMinimumWidth(160)
        self._refresh_image_combo()

        image_row = QHBoxLayout()
        image_row.addWidget(self.image_label)
        image_row.addWidget(self.image_combo, stretch=1)

        self.points_group = QGroupBox("ROI Corner Points")
        points_layout = QVBoxLayout()
        self.point_spins: list[tuple[QSpinBox, QSpinBox]] = []

        for i in range(4):
            b_spin = QSpinBox()
            lat_spin = QSpinBox()

            point_row = QHBoxLayout()
            point_row.addWidget(QLabel(f"P{i + 1}:"))
            point_row.addWidget(QLabel("B-Scan:"))
            point_row.addWidget(b_spin)
            point_row.addWidget(QLabel("Lateral:"))
            point_row.addWidget(lat_spin)
            points_layout.addLayout(point_row)

            self.point_spins.append((b_spin, lat_spin))

        self.points_group.setLayout(points_layout)

        self.apply_btn = QPushButton("Apply ROI")

        layout = QVBoxLayout()
        layout.addLayout(image_row)
        layout.addWidget(self.points_group)
        layout.addWidget(self.apply_btn)
        layout.addStretch()
        self.setLayout(layout)

        viewer.layers.events.inserted.connect(self._refresh_image_combo)
        viewer.layers.events.removed.connect(self._refresh_image_combo)

        self.image_combo.currentTextChanged.connect(self._on_image_changed)
        for b_spin, lat_spin in self.point_spins:
            b_spin.valueChanged.connect(self._update_preview)
            lat_spin.valueChanged.connect(self._update_preview)
        self.apply_btn.clicked.connect(self._on_apply)

        self._on_image_changed()

    def _refresh_image_combo(self, _event=None):
        current = self.image_combo.currentText()
        self.image_combo.blockSignals(True)
        self.image_combo.clear()
        self.image_combo.addItem("None")
        for layer in self.viewer.layers:
            if isinstance(layer, _get_napari_image_class()):
                self.image_combo.addItem(layer.name)
        idx = self.image_combo.findText(current)
        self.image_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.image_combo.blockSignals(False)

    def _on_image_changed(self, _=None):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        b_scans, _, lateral = image_layer.data.shape

        for b_spin, lat_spin in self.point_spins:
            b_spin.setRange(0, max(b_scans - 1, 0))
            lat_spin.setRange(0, max(lateral - 1, 0))

        defaults = [
            (0, 0),
            (0, lateral - 1),
            (b_scans - 1, lateral - 1),
            (b_scans - 1, 0),
        ]
        for (u_spin, v_spin), (u, v) in zip(self.point_spins, defaults):
            u_spin.blockSignals(True)
            v_spin.blockSignals(True)
            u_spin.setValue(u)
            v_spin.setValue(v)
            u_spin.blockSignals(False)
            v_spin.blockSignals(False)
        self._update_preview()

    def _get_points(self) -> list[tuple[int, int]]:
        return [
            (int(b_spin.value()), int(lat_spin.value()))
            for b_spin, lat_spin in self.point_spins
        ]

    def _update_preview(self, _=None):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        roi_corner_points = np.asarray(self._get_points(), dtype=np.int32)
        preview = fn._roi_to_volume(
            roi_corner_points,
            shape=image_layer.data.shape,
        ).astype(np.uint8)

        existing = [lay.name for lay in self.viewer.layers]
        if "_roi_preview" in existing:
            lay = self.viewer.layers["_roi_preview"]
            lay.data = preview
            lay.refresh()
        else:
            self.viewer.add_labels(
                preview,
                name="_roi_preview",
                affine=image_layer.affine.affine_matrix,
                scale=image_layer.scale,
                opacity=0.3,
            )

    def _on_apply(self):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        roi_corner_points = self._get_points()

        data = fn.define_roi(
            asarray(image_layer.data),
            roi_corner_points,
        )

        if "_roi" in image_layer.name:
            output_name = image_layer.name
        else:
            output_name = f"{image_layer.name}_roi"

        roi_metadata = {
            **image_layer.metadata,
            "roi_corner_points": [list(point) for point in roi_corner_points],
        }

        existing = [lay.name for lay in self.viewer.layers]
        if output_name in existing:
            lay = self.viewer.layers[output_name]
            lay.data = data
            lay.metadata = roi_metadata
            lay.refresh()
        else:
            self.viewer.add_image(
                data,
                name=output_name,
                affine=image_layer.affine.affine_matrix,
                metadata=roi_metadata,
                scale=image_layer.scale,
                axis_labels=image_layer.axis_labels,
                units=image_layer.units,
                contrast_limits=(0, 255) if data.dtype == np.uint8 else (0, 1),
            )

        recorder.record(
            function="define_roi",
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params={"roi_corner_points": [list(point) for point in roi_corner_points]},
        )
        panel = get_panel()
        if panel is not None:
            panel.refresh()

    def _get_selected_image_layer(self):
        name = self.image_combo.currentText()
        if not name or name == "None":
            return None
        try:
            layer = self.viewer.layers[name]
            return layer if isinstance(layer, _get_napari_image_class()) else None
        except KeyError:
            return None


@magic_factory(
    call_button="Remove Small Objects",
    max_object_size={
        "label": "Max Object Size",
        "min": 0,
        "tooltip": TOOLTIPS["remove_outliers"]["size"],
    },
)
def remove_small_objects_widget(
    labels: "napari.layers.Labels", max_object_size: int = 0
) -> "napari.types.LayerDataTuple":
    data = fn.remove_small_objects(asarray(labels.data), max_object_size)

    if "cleaned" in labels.name:
        output_name = labels.name
    else:
        output_name = f"{labels.name}_cleaned"

    recorder.record(
        function="remove_small_objects",
        input_layers={"labels": labels.name},
        output_layer=output_name,
        params={"max_object_size": max_object_size},
    )
    p = get_panel()
    if p is not None:
        p.refresh()

    napari_metadata = {
        "metadata": {**labels.metadata},
        "affine": labels.affine.affine_matrix,
        "units": labels.units,
        "axis_labels": labels.axis_labels,
        "scale": labels.scale,
        "opacity": labels.opacity,
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "labels"))


@magic_factory(call_button="Interpolate Gaps", surface={"label": "Surface"})
def interpolate_gaps_widget(
    surface: "napari.layers.Labels",
) -> "napari.types.LayerDataTuple":
    roi_corner_points = surface.metadata.get("roi_corner_points", None)
    interpolated = fn.interpolate_gaps(
        asarray(surface.data), roi_corner_points=roi_corner_points
    )

    if "interpolated" in surface.name:
        output_name = surface.name
    else:
        output_name = f"{surface.name}_interpolated"

    recorder.record(
        function="interpolate_gaps",
        input_layers={"surface": surface.name},
        output_layer=output_name,
        params={},
    )
    panel = get_panel()
    if panel is not None:
        panel.refresh()

    napari_metadata = {
        "metadata": {**surface.metadata},
        "affine": surface.affine.affine_matrix,
        "units": surface.units,
        "axis_labels": surface.axis_labels,
        "scale": surface.scale,
        "opacity": surface.opacity,
        # new layer_name
        "name": output_name,
    }

    return cast(
        "napari.types.LayerDataTuple", (interpolated, napari_metadata, "labels")
    )


@magic_factory(
    call_button="Zero Out Area",
    direction={
        "choices": ["above", "below"],
        "label": "Direction",
        "tooltip": TOOLTIPS["zero_out"]["direction"],
    },
    image={"label": "Image"},
)
def zero_out_area_widget(
    image: "napari.layers.Image",
    surface_coords: "napari.layers.Labels",
    direction: Literal["above", "below"] = "below",
) -> "napari.types.LayerDataTuple":
    data = fn.zero_out_area(
        asarray(image.data), asarray(surface_coords.data), direction
    )

    if "zeroed" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_zeroed"

    recorder.record(
        function="zero_out_area",
        input_layers={"image": image.name, "surface_coords": surface_coords.name},
        output_layer=output_name,
        params={"direction": direction},
    )
    panel = get_panel()
    if panel is not None:
        panel.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        "contrast_limits": (0, 255) if data.dtype == np.uint8 else (0, 1),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


@magic_factory(
    call_button="Replace Reflection",
    image={"label": "Image"},
    reflection={"label": "Reflection"},
    axial_offset={
        "label": "Axial Offset",
        "min": -500,
        "max": 500,
        "tooltip": TOOLTIPS["replace_reflection"]["offset"],
    },
    axial_padding={
        "label": "Axial Padding",
        "tooltip": TOOLTIPS["replace_reflection"]["padding"],
    },
)
def replace_reflection_widget(
    image: "napari.layers.Image",
    reflection: "napari.layers.Labels",
    axial_offset: int = 5,
    axial_padding: int = 2,
) -> "napari.types.LayerDataTuple":
    data = fn.replace_reflection(
        asarray(image.data), asarray(reflection.data), axial_padding, axial_offset
    )

    if "reflection_removed" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_reflection_removed"

    recorder.record(
        function="replace_reflection",
        input_layers={"image": image.name, "reflection": reflection.name},
        output_layer=output_name,
        params={"axial_offset": axial_offset, "axial_padding": axial_padding},
    )
    panel = get_panel()
    if panel is not None:
        panel.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        "contrast_limits": (0, 255) if data.dtype == np.uint8 else (0, 1),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


@magic_factory(
    call_button="Untilt Image",
    image={"label": "Image"},
    substratum_coords={"label": "Substratum Coords"},
)
def untilt_widget(
    image: "napari.layers.Layer", substratum_coords: "napari.layers.Labels"
) -> "napari.types.LayerDataTuple":
    data = fn.untilt(asarray(image.data), asarray(substratum_coords.data))

    if "untilted" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_untilted"

    recorder.record(
        function="untilt",
        input_layers={"image": image.name, "substratum_coords": substratum_coords.name},
        output_layer=output_name,
        params={},
    )
    panel = get_panel()
    if panel is not None:
        panel.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        # new layer_name
        "name": output_name,
    }
    if isinstance(image, _get_napari_image_class()):
        napari_metadata["contrast_limits"] = (
            (0, 255) if data.dtype == np.uint8 else (0, 1)
        )

    layer_type = image._type_string

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, layer_type))


@magic_factory(
    call_button="Enhance Contrast",
    image={"label": "Image"},
    method={"label": "Method", "tooltip": TOOLTIPS["contrast"]["method"]},
    gamma={
        "label": "Gamma",
        "min": 0.1,
        "step": 0.1,
        "tooltip": TOOLTIPS["contrast"]["gamma"],
    },
    clip_low_pct={
        "label": "Clip Low [%]",
        "min": 0.0,
        "max": 100.0,
        "step": 0.1,
        "tooltip": TOOLTIPS["contrast"]["clip_low_percentile"],
    },
    clip_high_pct={
        "label": "Clip High [%]",
        "min": 0.0,
        "max": 100.0,
        "step": 0.1,
        "tooltip": TOOLTIPS["contrast"]["clip_high_percentile"],
    },
    clahe_clip_limit={
        "label": "CLAHE Clip Limit",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
        "tooltip": TOOLTIPS["contrast"]["clahe_clip"],
    },
    clahe_tile_size={
        "label": "CLAHE Tile Size",
        "min": 1,
        "max": 64,
        "step": 1,
        "tooltip": TOOLTIPS["contrast"]["clahe_tile"],
    },
)
def enhance_contrast_widget(
    image: "napari.layers.Image",
    method: Literal["gamma", "clip", "clahe"] = "gamma",
    gamma: float = 1.0,
    clip_low_pct: float = 1.0,
    clip_high_pct: float = 99.0,
    clahe_clip_limit: float = 2.0,
    clahe_tile_size: int = 8,
) -> "napari.types.LayerDataTuple":
    data = fn.enhance_contrast(
        asarray(image.data),
        method=method,
        gamma=gamma,
        clip_low_pct=clip_low_pct,
        clip_high_pct=clip_high_pct,
        clahe_clip_limit=clahe_clip_limit,
        clahe_tile_size=clahe_tile_size,
    )

    if "enhanced" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_enhanced"

    recorder.record(
        function="enhance_contrast",
        input_layers={"image": image.name},
        output_layer=output_name,
        params={
            "method": method,
            **({"gamma": gamma} if method == "gamma" else {}),
            **({"clip_low_pct": clip_low_pct} if method == "clip" else {}),
            **({"clip_high_pct": clip_high_pct} if method == "clip" else {}),
            **({"clahe_clip_limit": clahe_clip_limit} if method == "clahe" else {}),
            **({"clahe_tile_size": clahe_tile_size} if method == "clahe" else {}),
        },
    )
    panel = get_panel()
    if panel is not None:
        panel.refresh()

    napari_metadata = {
        "metadata": {**image.metadata},
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        "contrast_limits": (0, 255) if data.dtype == np.uint8 else (0, 1),
        # new layer_name
        "name": output_name,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


# * Enhance contrast widget initialization which connects a callback to the method dropdown to show/hide related parameters
def _init_enhance_contrast_widget(widget):
    def _on_method_change(value):
        widget.gamma.visible = False
        widget.clip_low_pct.visible = False
        widget.clip_high_pct.visible = False
        widget.clahe_clip_limit.visible = False
        widget.clahe_tile_size.visible = False

        if value == "gamma":
            widget.gamma.visible = True
        elif value == "clip":
            widget.clip_low_pct.visible = True
            widget.clip_high_pct.visible = True
        elif value == "clahe":
            widget.clahe_clip_limit.visible = True
            widget.clahe_tile_size.visible = True

    widget.method.changed.connect(_on_method_change)
    _on_method_change(widget.method.value)


enhance_contrast_widget._widget_init = _init_enhance_contrast_widget


class ThresholdWidget(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer

        # --- Image selector ---
        self.image_label = QLabel("Image:")
        self.image_combo = QComboBox()
        self.image_combo.setMinimumWidth(160)
        self._refresh_image_combo()

        image_row = QHBoxLayout()
        image_row.addWidget(self.image_label)
        image_row.addWidget(self.image_combo, stretch=1)

        # --- Method checkboxes ---
        methods_group = QGroupBox("Threshold Methods")
        methods_layout = QVBoxLayout()

        self.method_checks: dict[str, QCheckBox] = {}
        for m in THRESHOLD_METHODS:
            cb = QCheckBox(m)
            # cb.setChecked(m in ("otsu", "triangle"))
            self.method_checks[m] = cb
            methods_layout.addWidget(cb)

        # Manual value spinbox (only enabled when "manual" is checked)
        self.manual_spin = QSpinBox()
        self.manual_spin.setRange(0, 255)
        self.manual_spin.setValue(128)
        self.manual_spin.setEnabled(False)
        manual_row = QHBoxLayout()
        manual_row.addSpacing(20)
        manual_row.addWidget(QLabel("Value:"))
        manual_row.addWidget(self.manual_spin)
        methods_layout.addLayout(manual_row)

        # Mark all / Unmark all
        mark_row = QHBoxLayout()
        self.mark_all_btn = QPushButton("☑︎ Mark All")
        self.unmark_all_btn = QPushButton("☐ Unmark All")
        mark_row.addWidget(self.mark_all_btn)
        mark_row.addWidget(self.unmark_all_btn)
        methods_layout.addLayout(mark_row)

        methods_group.setLayout(methods_layout)

        # --- Preview button ---
        self.preview_btn = QPushButton("🔍 Preview (current B-Scan)")

        # --- Apply method section ---
        apply_label = QLabel("Apply method:")
        self.apply_combo = QComboBox()
        self._refresh_apply_combo()

        apply_row = QHBoxLayout()
        apply_row.addWidget(apply_label)
        apply_row.addWidget(self.apply_combo, stretch=1)

        # --- Color selection ---
        self.color_label = QLabel("Set Color:")
        self.color_combo = QComboBox()
        for name in COLORMAP:
            self.color_combo.addItem(name)
        self.color_combo.setCurrentText("Yellow")

        color_row = QHBoxLayout()
        color_row.addWidget(self.color_label)
        color_row.addWidget(self.color_combo)

        # --- Apply button ---
        self.apply_btn = QPushButton("▶ Apply (full stack)")

        # --- Layout ---
        layout = QVBoxLayout()
        layout.addLayout(image_row)
        layout.addWidget(methods_group)
        layout.addWidget(self.preview_btn)
        layout.addLayout(apply_row)
        layout.addLayout(color_row)
        layout.addWidget(self.apply_btn)
        layout.addStretch()
        self.setLayout(layout)

        # --- Signals ---
        viewer.layers.events.inserted.connect(self._refresh_image_combo)
        viewer.layers.events.removed.connect(self._refresh_image_combo)
        self.method_checks["manual"].toggled.connect(self.manual_spin.setEnabled)
        for cb in self.method_checks.values():
            cb.toggled.connect(self._refresh_apply_combo)
        self.mark_all_btn.clicked.connect(self._mark_all)
        self.unmark_all_btn.clicked.connect(self._unmark_all)
        self.preview_btn.clicked.connect(self._on_preview)
        self.apply_btn.clicked.connect(self._on_apply)

    def _refresh_image_combo(self, _event=None):
        current = self.image_combo.currentText()
        self.image_combo.blockSignals(True)
        self.image_combo.clear()
        self.image_combo.addItem("None")
        for layer in self.viewer.layers:
            if isinstance(layer, _get_napari_image_class()):
                self.image_combo.addItem(layer.name)
        idx = self.image_combo.findText(current)
        self.image_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.image_combo.blockSignals(False)

    def _refresh_apply_combo(self, _=None):
        current = self.apply_combo.currentText()
        self.apply_combo.blockSignals(True)
        self.apply_combo.clear()
        for m, cb in self.method_checks.items():
            if cb.isChecked():
                self.apply_combo.addItem(m)
        idx = self.apply_combo.findText(current)
        if idx >= 0:
            self.apply_combo.setCurrentIndex(idx)
        self.apply_combo.blockSignals(False)

    def _mark_all(self):
        for cb in self.method_checks.values():
            cb.setChecked(True)

    def _unmark_all(self):
        for cb in self.method_checks.values():
            cb.setChecked(False)

    def _get_selected_image_layer(self):
        name = self.image_combo.currentText()
        if not name or name == "None":
            return None
        try:
            layer = self.viewer.layers[name]
            return layer if isinstance(layer, _get_napari_image_class()) else None
        except KeyError:
            return None

    def _on_preview(self):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return
        methods = [m for m, cb in self.method_checks.items() if cb.isChecked()]
        if not methods:
            return

        b_idx = int(self.viewer.dims.current_step[0])
        b_idx = max(0, min(b_idx, image_layer.data.shape[0] - 1))
        bscan = asarray(image_layer.data[b_idx])
        manual_val = self.manual_spin.value()

        fn._plot_thresholds(
            image=bscan,
            thresholds=fn._calc_thresholds(bscan, methods, manual_val),
            b_idx=b_idx,
        )

    def _on_apply(self):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return
        method = self.apply_combo.currentText()
        if not method:
            return
        manual_threshold = self.manual_spin.value()
        label_color = self.color_combo.currentText()
        color_id = COLORMAP[label_color]

        data = fn.threshold(
            asarray(image_layer.data), method, manual_threshold, color_id=color_id
        )

        output_name = f"{image_layer.name}_binary"

        existing = [lay.name for lay in self.viewer.layers]
        if output_name in existing:
            lay = self.viewer.layers[output_name]
            lay.data = data
            lay.refresh()
        else:
            self.viewer.add_labels(
                data,
                name=output_name,
                affine=image_layer.affine.affine_matrix,
                metadata={**image_layer.metadata},
                scale=image_layer.scale,
                axis_labels=image_layer.axis_labels,
                units=image_layer.units,
                opacity=1.0,
            )

        recorder.record(
            function="threshold",
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params={
                "method": method,
                **(
                    {"manual_threshold": manual_threshold} if method == "manual" else {}
                ),
            },
        )
        p = get_panel()
        if p is not None:
            p.refresh()


@magic_factory(
    call_button="Export to TIFF",
    image={"label": "Image"},
)
def export_to_tiff_widget(image: "napari.layers.Layer") -> None:
    source_dir = Path(image.metadata["source_dir"])
    savepath = source_dir / f"{image.name}.tiff"

    fn.export_to_tiff(
        image=asarray(image.data),
        spacing=asarray(image.metadata["spacing"]),
        path=savepath,
    )

    recorder.record(
        function="export_to_tiff",
        input_layers={"image": image.name},
        output_layer=None,
        params={
            "spacing": image.metadata[
                "spacing"
            ],  # * should stay the same for a batch -> keep static in record+replay
            "path": f"{SOURCE_DIR_PLACEHOLDER}/{LAYER_NAME_PLACEHOLDER}.tiff",
        },
    )
    p = get_panel()
    if p is not None:
        p.refresh()


@magic_factory(
    call_button="Export to NIfTI",
    image={"label": "Image"},
)
def export_to_nifti_widget(image: "napari.layers.Layer") -> None:
    source_dir = Path(image.metadata["source_dir"])
    savepath = source_dir / f"{image.name}.nii.gz"

    fn.export_to_nifti(
        image=asarray(image.data),
        affine=asarray(image.affine.affine_matrix),
        path=savepath,
    )

    recorder.record(
        function="export_to_nifti",
        input_layers={"image": image.name},
        output_layer=None,
        params={
            "affine": image.affine.affine_matrix.tolist(),  # * should stay the same for a batch -> keep static in record+replay
            "path": f"{SOURCE_DIR_PLACEHOLDER}/{LAYER_NAME_PLACEHOLDER}.nii.gz",
        },
    )
    p = get_panel()
    if p is not None:
        p.refresh()


@magic_factory(
    call_button="Create Height Map",
    segmentation={"label": "Segmentation"},
    substratum={"label": "Substratum"},
    colorbar={"label": "Add Colorbar"},
    scalebar={"label": "Add Scalebar"},
    axes={"label": "Show Axes"},
    max_height_um={
        "label": "Max Height [µm]",
        "max": 10000,
        "tooltip": TOOLTIPS["h_map"]["max_h"],
    },
    preview={"label": "Preview", "tooltip": TOOLTIPS["h_map"]["preview"]},
)
def create_height_map_widget(
    segmentation: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
    max_height_um: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
    preview: bool = True,
) -> None:
    source_dir = Path(segmentation.metadata.get("source_dir", Path.home()))
    path = source_dir / f"{segmentation.name}_Hmap.tiff"

    spacing = segmentation.metadata.get("spacing", None)

    fn.create_height_map(
        segmentation=asarray(segmentation.data),
        substratum=asarray(substratum.data) if substratum is not None else None,
        spacing=asarray(spacing) if spacing is not None else None,
        max_height_um=max_height_um,
        colorbar=colorbar,
        scalebar=scalebar,
        preview=preview,
        axes=axes,
        path=path,
    )

    if not preview:
        recorder.record(
            function="create_height_map",
            input_layers={
                "segmentation": segmentation.name,
                **({"substratum": substratum.name} if substratum is not None else {}),
            },
            output_layer=None,
            params={
                "spacing": spacing,  # * should stay the same for a batch -> keep static in record+replay
                "max_height_um": max_height_um,
                "colorbar": colorbar,
                "scalebar": scalebar,
                "axes": axes,
                "path": f"{SOURCE_DIR_PLACEHOLDER}/{LAYER_NAME_PLACEHOLDER}_Hmap.tiff",
            },
        )
        p = get_panel()
        if p is not None:
            p.refresh()


@magic_factory(
    call_button="Create Biovolume Map",
    segmentation={"label": "Segmentation"},
    substratum={"label": "Substratum"},
    colorbar={"label": "Add Colorbar"},
    scalebar={"label": "Add Scalebar"},
    axes={"label": "Show Axes"},
    max_height_um={
        "label": "Max Height [µm]",
        "max": 10000,
        "tooltip": TOOLTIPS["bv_map"]["max_h"],
    },
    preview={"label": "Preview", "tooltip": TOOLTIPS["bv_map"]["preview"]},
)
def create_bv_map_widget(
    segmentation: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
    max_height_um: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
    preview: bool = True,
) -> None:
    source_dir = Path(segmentation.metadata.get("source_dir", Path.home()))
    path = source_dir / f"{segmentation.name}_BVmap.tiff"

    spacing = segmentation.metadata.get("spacing", None)

    fn.create_bv_map(
        segmentation=asarray(segmentation.data),
        substratum=asarray(substratum.data) if substratum is not None else None,
        spacing=asarray(spacing) if spacing is not None else None,
        max_height_um=max_height_um,
        colorbar=colorbar,
        scalebar=scalebar,
        preview=preview,
        axes=axes,
        path=path,
    )

    if not preview:
        recorder.record(
            function="create_bv_map",
            input_layers={
                "segmentation": segmentation.name,
                **({"substratum": substratum.name} if substratum is not None else {}),
            },
            output_layer=None,
            params={
                "spacing": spacing,  # * should stay the same for a batch -> keep static in record+replay
                "max_height_um": max_height_um,
                "colorbar": colorbar,
                "scalebar": scalebar,
                "axes": axes,
                "path": f"{SOURCE_DIR_PLACEHOLDER}/{LAYER_NAME_PLACEHOLDER}_BVmap.tiff",
            },
        )
        p = get_panel()
        if p is not None:
            p.refresh()


@magic_factory(
    call_button="Save Metrics to CSV",
    segmentation={"label": "Segmentation"},
    substratum={"label": "Substratum"},
)
def calculate_metrics_widget(
    segmentation: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
) -> None:
    source_dir = Path(segmentation.metadata.get("source_dir", Path.home()))
    path = source_dir / f"{segmentation.name}_metrics.csv"
    batch_export_path = f"{SOURCE_DIR_PLACEHOLDER}/batch_metrics.csv"

    spacing = segmentation.metadata.get("spacing")
    assert spacing is not None

    roi_corner_points = segmentation.metadata.get("roi_corner_points", None)
    if roi_corner_points is not None:
        roi_corner_points = np.asarray(roi_corner_points, dtype=np.int32).tolist()

    fn.calculate_metrics(
        asarray(segmentation.data),
        segmentation.name,
        Path(path),
        asarray(spacing),
        asarray(substratum.data) if substratum is not None else None,
        roi_corner_points=roi_corner_points,
    )

    record_params = {"spacing": spacing, "path": batch_export_path}
    if roi_corner_points is not None:
        record_params["roi_corner_points"] = roi_corner_points

    recorder.record(
        function="calculate_metrics",
        input_layers={
            "segmentation": segmentation.name,
            **({"substratum": substratum.name} if substratum is not None else {}),
        },
        output_layer=None,
        params=record_params,
    )
    p = get_panel()
    if p is not None:
        p.refresh()


# endregion WIDGETS


# region WIDGET_DEV
@magic_factory(
    call_button="Set Spacing",
    spacing_bscans={"label": "B-Scan Spacing [Y]", "widget_type": "LineEdit"},
    spacing_axial={"label": "Axial Spacing [Z]", "widget_type": "LineEdit"},
    spacing_lateral={"label": "Lateral Spacing [X]", "widget_type": "LineEdit"},
)
def set_spacing_widget(
    layer: "napari.layers.Layer",
    spacing_bscans: str,
    spacing_axial: str,
    spacing_lateral: str,
):
    layer.metadata["spacing"] = (
        float(spacing_bscans),
        float(spacing_axial),
        float(spacing_lateral),
    )
    if hasattr(layer, "affine") and layer.affine is not None:
        # Update affine matrix to reflect new spacing
        new_affine = np.copy(layer.affine.affine_matrix)
        np.fill_diagonal(new_affine, list(layer.metadata["spacing"]) + [1])
        layer.affine = new_affine
    layer.refresh()


@magic_factory(
    call_button="Preview Height Map",
    max_h={"label": "Max Height [µm]", "max": 10000},
)
def preview_height_map_widget(
    binary: "napari.layers.Labels",
    substratum: "napari.layers.Labels | None" = None,
    max_h: int = 0,
) -> "napari.types.LayerDataTuple":
    spacing = binary.metadata.get("spacing", None)
    axial_spacing = spacing[1] if spacing is not None else None

    data = fn._calc_height_map(
        binary=asarray(binary.data),
        substratum=asarray(substratum.data) if substratum is not None else None,
        axial_spacing=axial_spacing,
    )

    napari_metadata = {
        "name": f"{binary.name}_hm_preview",
        "colormap": "inferno",
        "scale": (0.3, 0.3),
        "contrast_limits": (0, max_h),
        "opacity": 1.0,
    }

    return cast("napari.types.LayerDataTuple", (data, napari_metadata, "image"))


@magic_factory(
    call_button="Print Metadata",
    result_widget=True,
)
def print_metadata(layer: "napari.layers.Layer"):
    info = {
        "metadata": layer.metadata,
        "name": layer.name,
        "affine": layer.affine.affine_matrix,
        "scale": layer.scale,
        "opacity": layer.opacity,
        "source": layer.source,
        "units": layer.units,
        "ndim": layer.ndim,
        "contrast_limits": layer.contrast_limits
        if isinstance(layer, _get_napari_image_class())
        else None,
        "layer_type": layer._type_string,
    }
    return json.dumps(info, indent=2, default=str)


@magic_factory(
    call_button="Expand Surface",
    expand={"label": "Expand by [px]", "min": 0, "max": 10, "widget_type": "Slider"},
)
def expand_coords(
    coords: "napari.layers.Labels", expand: int = 0
) -> "napari.types.LayerDataTuple":
    label = fn._get_color_id(asarray(coords.data))
    surface = np.argmax(asarray(coords.data), axis=1)
    z = np.arange(coords.data.shape[1])[None, :, None]

    mask = (z >= (surface[:, None, :] - expand)) & (z <= (surface[:, None, :] + expand))
    mask = mask.astype(np.uint8) * label

    napari_metadata = {
        "metadata": {**coords.metadata},
        "affine": coords.affine.affine_matrix,
        "units": coords.units,
        "axis_labels": coords.axis_labels,
        "scale": coords.scale,
        "opacity": coords.opacity,
        # new layer_name
        "name": f"{coords.name}_expanded",
    }

    return cast("napari.types.LayerDataTuple", (mask, napari_metadata, "labels"))


# endregion WIDGET_DEV


def _get_napari_image_class():
    import napari.layers

    return napari.layers.Image
