# region IMPORTS
# Python native imports
from typing import Literal, cast
from pathlib import Path
import json

# Third party imports
from magicgui import magic_factory
from napari.layers import Image, Labels, Layer
from napari.types import LayerDataTuple
import napari.viewer
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
)


COLORMAP: dict[str, int] = {
    "Cyan": 2,
    "Yellow": 9,
    "Red": 10,
    "Blue": 34,
    "Green": 37,
    "Purple": 45,
}
# endregion IMPORTS


# region WIDGETS
@magic_factory(call_button="Convert to 8bit")
def convert_to_8bit_widget(image: Image) -> LayerDataTuple:
    data = fn.convert_to_8bit(asarray(image.data))

    napari_metadata = {
        "metadata": {**image.metadata},
        "name": image.name,
        "affine": image.affine.affine_matrix,
        "units": image.units,
        "axis_labels": image.axis_labels,
        "scale": image.scale,
        "opacity": image.opacity,
        # new contrast limits for unit8
        "contrast_limits": (0, 255),
    }

    recorder.record(
        function=Fn.CONVERT_TO_8BIT,
        input_layers={"image": image.name},
        output_layer=image.name,
        params={},
    )
    p = get_panel()
    if p is not None:
        p.refresh()

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


@magic_factory(
    call_button="Apply Median Filter",
    size={
        "min": 1,
        "step": 2,
        "max": 13,
        "tooltip": "Size of the neighborhood (must be odd). A larger size means more aggressive filtering.",
    },
)
def median_filter_widget(image: Image, size: int = 1) -> LayerDataTuple:
    """
    Apply a 2D median filter to each B-Scan of the selected image.
    A median filter replaces each pixel with the median value of its neighborhood.
    The 'size' parameter determines the size of the neighborhood (must be odd so it has a single center pixel).
    Median filters are effective at removing noise while preserving edges.
    """
    data = fn.median_filter(asarray(image.data), size)

    if "median" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_median"

    # Recording
    recorder.record(
        function=Fn.MEDIAN_FILTER,
        input_layers={"image": image.name},
        output_layer=output_name,
        params={"size": size},
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


@magic_factory(call_button="Apply Gaussian Filter", sigma={"max": 20.0})
def gaussian_filter_widget(image: Image, sigma: float = 0.0) -> LayerDataTuple:
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


@magic_factory(
    call_button="Apply Sobel Filter",
)
def sobel_filter_widget(
    image: Image,
) -> LayerDataTuple:
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


class LocateIntensityWidget(QWidget):
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
        self.ymin_label = QLabel("ymin  (Top Border):")
        self.ymin_spin = QSpinBox()

        ymin_row = QHBoxLayout()
        ymin_row.addWidget(self.ymin_label)
        ymin_row.addWidget(self.ymin_spin)

        # --- ymax ---
        self.ymax_label = QLabel("ymax  (Bottom Border):")
        self.ymax_spin = QSpinBox()

        ymax_row = QHBoxLayout()
        ymax_row.addWidget(self.ymax_label)
        ymax_row.addWidget(self.ymax_spin)

        # --- y_offset ---
        self.offset_label = QLabel("Offset:")
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
            if isinstance(layer, Image):
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

        ymin = int(self.ymin_spin.value())
        ymax = int(self.ymax_spin.value())
        offset = int(self.offset_spin.value())

        label_color = self.color_combo.currentText()
        label_id = COLORMAP[label_color]

        coords = fn.locate_intensity(
            asarray(image_layer.data), ymin, ymax, offset, label_id
        )

        output_name = f"{image_layer.name}_intensity-coords"

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
        recorder.record(
            function="locate_intensity",
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params={"ymin": ymin, "ymax": ymax, "y_offset": offset},
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
            return layer if isinstance(layer, Image) else None
        except KeyError:
            return None


@magic_factory(
    call_button="Remove Small objects", size={"label": "Object Size", "min": 0}
)
def remove_outliers_widget(image: Labels, size: int = 0) -> LayerDataTuple:
    data = fn.remove_outliers(asarray(image.data), size)

    if "cleaned" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_cleaned"

    recorder.record(
        function="remove_outliers",
        input_layers={"image": image.name},
        output_layer=output_name,
        params={"outlier_size": size},
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
        # new layer_name
        "name": output_name,
    }

    return cast(LayerDataTuple, (data, napari_metadata, "labels"))


@magic_factory(call_button="Interpolate Gaps")
def interpolate_gaps_widget(image: Labels) -> LayerDataTuple:
    interpolated = fn.interpolate_gaps(asarray(image.data))

    if "interpolated" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_interpolated"

    recorder.record(
        function="interpolate_gaps",
        input_layers={"image": image.name},
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

    return cast(LayerDataTuple, (interpolated, napari_metadata, "labels"))


@magic_factory(
    call_button="Zero Out Area",
    direction={"choices": ["above", "below"], "label": "Direction"},
)
def zero_out_widget(
    image: Image, labels: Labels, direction: Literal["above", "below"] = "below"
) -> LayerDataTuple:
    data = fn.zero_out(asarray(image.data), asarray(labels.data), direction)

    if "zeroed" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_zeroed"

    recorder.record(
        function="zero_out",
        input_layers={"image": image.name, "labels": labels.name},
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


@magic_factory(
    call_button="Replace Reflection",
    offset={"label": "Axial Offset", "min": -500, "max": 500},
    padding={"label": "Padding"},
)
def replace_reflection_widget(
    image: Image, reflection: Labels, offset: int = 5, padding: int = 2
) -> LayerDataTuple:
    data = fn.replace_reflection(
        asarray(image.data), asarray(reflection.data), padding, offset
    )

    if "reflection_removed" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_reflection_removed"

    recorder.record(
        function="replace_reflection",
        input_layers={"image": image.name, "labels": reflection.name},
        output_layer=output_name,
        params={"offset": offset, "padding": padding},
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


@magic_factory(call_button="Untilt Image")
def untilt_widget(image: Layer, coords: Labels) -> LayerDataTuple:
    data = fn.untilt(asarray(image.data), asarray(coords.data))

    if "untilted" in image.name:
        output_name = image.name
    else:
        output_name = f"{image.name}_untilted"

    recorder.record(
        function="untilt",
        input_layers={"image": image.name, "labels": coords.name},
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
    if isinstance(image, Image):
        napari_metadata["contrast_limits"] = (
            (0, 255) if data.dtype == np.uint8 else (0, 1)
        )

    layer_type = image._type_string

    return cast(LayerDataTuple, (data, napari_metadata, layer_type))


@magic_factory(
    call_button="Enhance Contrast",
    header={
        "widget_type": "Label",
        "label": "<b>Contrast Enhancement</b><br>"
        "<small>"
        "Improve image visibility using different contrast adjustment methods:<br><br>"
        "<b>Gamma:</b> Adjusts brightness non-linearly. Useful for overall light/dark correction.<br>"
        "<b>Clipping:</b> Stretches contrast by cutting off extreme low/high intensities.<br>"
        "<b>CLAHE:</b> Enhances local contrast while limiting noise amplification."
        "</small>",
    },
    method={"label": "Method"},
    gamma={"label": "Gamma", "min": 0.1, "step": 0.1},
    clip_low_percentile={
        "label": "Clip Low [%]",
        "min": 0.0,
        "max": 100.0,
        "step": 0.1,
    },
    clip_high_percentile={
        "label": "Clip High [%]",
        "min": 0.0,
        "max": 100.0,
        "step": 0.1,
    },
    clahe_clip={
        "label": "CLAHE Clip",
        "min": 0.1,
        "max": 10.0,
        "step": 0.1,
        "tooltip": "Controls how strongly contrast is enhanced. Lower values yield small but stable contrast increase. Higher values increase contrast more but may amplify noise.",
    },
    clahe_tile={
        "label": "CLAHE Tile Size",
        "min": 1,
        "max": 64,
        "step": 1,
        "tooltip": "Sets the size of local regions used for contrast enhancement. Smaller tiles reveal more detail but can introduce artifacts. Larger tiles behave closer to global contrast enhancement.",
    },
)
def enhance_contrast_widget(
    header,
    image: Image,
    method: Literal["gamma", "clip", "clahe"] = "gamma",
    gamma: float = 1.0,
    clip_low_percentile: float = 1.0,
    clip_high_percentile: float = 99.0,
    clahe_clip: float = 2.0,
    clahe_tile: int = 8,
) -> LayerDataTuple:
    data = fn.enhance_contrast(
        asarray(image.data),
        method=method,
        gamma=gamma,
        clip_low_percentile=clip_low_percentile,
        clip_high_percentile=clip_high_percentile,
        clahe_clip=clahe_clip,
        clahe_tile=clahe_tile,
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
            **(
                {"clip_low_percentile": clip_low_percentile} if method == "clip" else {}
            ),
            **(
                {"clip_high_percentile": clip_high_percentile}
                if method == "clip"
                else {}
            ),
            **({"clahe_clip": clahe_clip} if method == "clahe" else {}),
            **({"clahe_tile": clahe_tile} if method == "clahe" else {}),
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


# * Enhance contrast widget initialization which connects a callback to the method dropdown to show/hide related parameters
def _init(widget):
    def _on_method_change(value):
        widget.gamma.visible = False
        widget.clip_low_percentile.visible = False
        widget.clip_high_percentile.visible = False
        widget.clahe_clip.visible = False
        widget.clahe_tile.visible = False

        if value == "gamma":
            widget.gamma.visible = True
        elif value == "clip":
            widget.clip_low_percentile.visible = True
            widget.clip_high_percentile.visible = True
        elif value == "clahe":
            widget.clahe_clip.visible = True
            widget.clahe_tile.visible = True

    widget.method.changed.connect(_on_method_change)
    _on_method_change(widget.method.value)


enhance_contrast_widget._widget_init = _init


class ThresholdWidget(QWidget):
    # TODO: Add ignore_black/ignore_white checkboxes for preview + apply -> so above methods checkboxes?
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
            if isinstance(layer, Image):
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
            return layer if isinstance(layer, Image) else None
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
        manual_val = self.manual_spin.value()
        label_color = self.color_combo.currentText()
        label_id = COLORMAP[label_color]

        data = fn.threshold(
            asarray(image_layer.data), method, manual_val, color_id=label_id
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
            params={"method": method, "manual_value": manual_val},
        )
        p = get_panel()
        if p is not None:
            p.refresh()


@magic_factory(
    call_button="Export to TIFF",
)
def export_to_tiff_widget(image: Layer) -> None:
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
)
def export_to_nifti_widget(image: Layer) -> None:
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
    max_h={"label": "Max Height [µm]", "max": 10000},
    preview={"label": "Preview (uncheck to save to file)"},
)
def height_map_widget(
    binary: Labels,
    substratum: Labels | None = None,
    max_h: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
    preview: bool = True,
) -> None:
    source_dir = Path(binary.metadata.get("source_dir", Path.home()))
    savepath = source_dir / f"{binary.name}_Hmap.tiff"

    spacing = binary.metadata.get("spacing", None)

    fn.create_height_map(
        binary=asarray(binary.data),
        substratum=asarray(substratum.data) if substratum is not None else None,
        spacing=asarray(spacing) if spacing is not None else None,
        max_h=max_h,
        colorbar=colorbar,
        scalebar=scalebar,
        preview=preview,
        axes=axes,
        savepath=savepath,
    )

    recorder.record(
        function="create_height_map",
        input_layers={
            "binary": binary.name,
            **({"substratum": substratum.name} if substratum is not None else {}),
        },
        output_layer=None,
        params={
            "spacing": spacing,  # * should stay the same for a batch -> keep static in record+replay
            "max_h": max_h,
            "colorbar": colorbar,
            "scalebar": scalebar,
            "axes": axes,
            "savepath": f"{SOURCE_DIR_PLACEHOLDER}/{LAYER_NAME_PLACEHOLDER}_Hmap.tiff",
        },
    )
    p = get_panel()
    if p is not None:
        p.refresh()


@magic_factory(
    call_button="Create Biovolume Map",
    max_h={
        "label": "Max Height [µm]",
        "max": 10000,
        "tooltip": "Will be converted to Volume (µm³) with spacing info.",
    },
    preview={"label": "Preview (uncheck to save to file)"},
)
def bv_map_widget(
    binary: Labels,
    substratum: Labels | None = None,
    max_h: int = 0,
    colorbar: bool = False,
    scalebar: bool = False,
    axes: bool = False,
    preview: bool = True,
) -> None:
    source_dir = Path(binary.metadata.get("source_dir", Path.home()))
    savepath = source_dir / f"{binary.name}_BVmap.tiff"

    spacing = binary.metadata.get("spacing", None)

    fn.create_bv_map(
        binary=asarray(binary.data),
        substratum=asarray(substratum.data) if substratum is not None else None,
        spacing=asarray(spacing) if spacing is not None else None,
        max_h=max_h,
        colorbar=colorbar,
        scalebar=scalebar,
        preview=preview,
        axes=axes,
        savepath=savepath,
    )

    recorder.record(
        function="create_bv_map",
        input_layers={
            "binary": binary.name,
            **({"substratum": substratum.name} if substratum is not None else {}),
        },
        output_layer=None,
        params={
            "spacing": spacing,  # * should stay the same for a batch -> keep static in record+replay
            "max_h": max_h,
            "colorbar": colorbar,
            "scalebar": scalebar,
            "axes": axes,
            "savepath": f"{SOURCE_DIR_PLACEHOLDER}/{LAYER_NAME_PLACEHOLDER}_BVmap.tiff",
        },
    )
    p = get_panel()
    if p is not None:
        p.refresh()


@magic_factory(
    call_button="Save Metrics to CSV",
    savepath={"mode": "w", "label": "Save as:", "filter": "*.csv"},
)
def save_metrics_widget(
    binary: Labels,
    substratum: Labels | None = None,
    savepath: Path = Path.home(),
    # filename: str = ">give_a_filename<",
    batch_export_path: str = "Path\\to\\batch_metrics.csv",
) -> None:
    # source_dir = Path(binary.metadata.get("source_dir", Path.home()))
    # savepath = source_dir / f"{binary.name}_BVmap.tiff"

    spacing = binary.metadata.get("spacing")
    assert spacing is not None

    fn.save_metrics(
        asarray(binary.data),
        binary.name,
        Path(savepath),
        asarray(spacing),
        asarray(substratum.data) if substratum is not None else None,
    )

    recorder.record(
        function="save_metrics",
        input_layers={
            "binary": binary.name,
            **({"substratum": substratum.name} if substratum is not None else {}),
        },
        output_layer=None,
        params={"spacing": spacing, "savepath": batch_export_path},
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
    layer: Layer, spacing_bscans: str, spacing_axial: str, spacing_lateral: str
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
    binary: Labels,
    substratum: Labels | None = None,
    max_h: int = 0,
) -> LayerDataTuple:
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

    return cast(LayerDataTuple, (data, napari_metadata, "image"))


@magic_factory(
    call_button="Print Metadata",
    result_widget=True,
)
def print_metadata(layer: Layer):
    info = {
        "metadata": layer.metadata,
        "name": layer.name,
        "affine": layer.affine.affine_matrix,
        "scale": layer.scale,
        "opacity": layer.opacity,
        "source": layer.source,
        "units": layer.units,
        "ndim": layer.ndim,
        "contrast_limits": layer.contrast_limits if isinstance(layer, Image) else None,
        "layer_type": layer._type_string,
    }
    return json.dumps(info, indent=2, default=str)


# endregion WIDGET_DEV
