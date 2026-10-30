from typing import TYPE_CHECKING

import numpy as np

# Third party imports
from numpy import asarray
from qtpy.QtWidgets import (
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
from ..shared_utility import copy_layer_properties, derive_name
from ._widget_helpers import _get_napari_image_class, _run_and_record_action

if TYPE_CHECKING:
    import napari.viewer


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
        self.image_combo.setCurrentIndex(max(idx, 0))
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
            self.viewer.add_labels(  # type: ignore[attr-defined]
                preview,
                name="_roi_preview",
                affine=image_layer.affine.affine_matrix,
                opacity=0.3,
            )

    def _on_apply(self):
        image_layer = self._get_selected_image_layer()
        if image_layer is None:
            return

        roi_corner_points = self._get_points()

        output_name = derive_name(image_layer.name, "roi")

        params = {"roi_corner_points": roi_corner_points}
        data = _run_and_record_action(
            func=fn.define_roi,
            inputs={"image": asarray(image_layer.data)},
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params=params,
        )

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
            layer_properties = {
                **copy_layer_properties(image_layer),
                "metadata": roi_metadata,
            }
            self.viewer.add_image(
                data,
                name=output_name,
                **layer_properties,
            )

    def _get_selected_image_layer(self):
        name = self.image_combo.currentText()
        if not name or name == "None":
            return None
        try:
            layer = self.viewer.layers[name]
            return layer if isinstance(layer, _get_napari_image_class()) else None
        except KeyError:
            return None
