from typing import TYPE_CHECKING

from numpy import asarray
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Local imports
from ..functions import functions as fn
from ..functions._function_helpers import _calc_thresholds, _plot_thresholds
from ..shared_utility import (
    COLORMAP,
    THRESHOLD_METHODS,
    copy_layer_properties,
    derive_name,
)
from ._widget_helpers import _get_napari_image_class, _run_and_record_action

if TYPE_CHECKING:
    import napari.viewer


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
        self.image_combo.setCurrentIndex(max(idx, 0))
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

        _plot_thresholds(
            image=bscan,
            thresholds=_calc_thresholds(bscan, methods, manual_val),
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

        output_name = derive_name(image_layer.name, "binary")
        params = {
            "method": method,
            "manual_threshold": manual_threshold,
            "color_id": color_id,
        }
        data = _run_and_record_action(
            func=fn.threshold,
            inputs={"image": asarray(image_layer.data)},
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params=params,
        )

        existing = [lay.name for lay in self.viewer.layers]
        if output_name in existing:
            lay = self.viewer.layers[output_name]
            lay.data = data
            lay.refresh()
        else:
            self.viewer.add_labels(  # type: ignore[attr-defined]
                data,
                name=output_name,
                **copy_layer_properties(image_layer, include_contrast_limit=False),
                opacity=1.0,
            )
