from typing import TYPE_CHECKING, cast

from magicgui import magic_factory
from numpy import asarray
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

# Local imports
from ..functions import functions as fn
from ..functions._function_helpers import _visualize_search_area
from ..shared_utility import COLORMAP, copy_layer_properties, derive_name
from ._widget_helpers import _get_napari_image_class, _run_and_record_action

if TYPE_CHECKING:
    import napari.layers
    import napari.types
    import napari.viewer


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

        search_area = _visualize_search_area(shape, ymin, ymax)

        existing = [lay.name for lay in self.viewer.layers]
        if "_search_window" in existing:
            lay = self.viewer.layers["_search_window"]
            lay.data = search_area
            lay.refresh()
        else:
            lay = self.viewer.add_labels(  # type: ignore[attr-defined]
                search_area,
                name="_search_window",
                affine=image_layer.affine.affine_matrix,
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

        output_name = derive_name(image_layer.name, "surface-coords")
        params = {
            "upper_bound": upper_bound,
            "lower_bound": lower_bound,
            "axial_offset": axial_offset,
            "color_id": color_id,
        }
        coords = _run_and_record_action(
            func=fn.locate_surface,
            inputs={"image": asarray(image_layer.data)},
            input_layers={"image": image_layer.name},
            output_layer=output_name,
            params=params,
        )

        existing = [lay.name for lay in self.viewer.layers]
        if output_name in existing:
            lay = self.viewer.layers[output_name]
            lay.data = coords
            lay.refresh()
        else:
            self.viewer.add_labels(  # type: ignore[attr-defined]
                coords,
                **copy_layer_properties(image_layer, include_contrast_limit=False),
                name=output_name,
                opacity=1.0,
            )

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


@magic_factory(call_button="Interpolate Gaps", surface={"label": "Surface"})
def interpolate_gaps_widget(
    surface: "napari.layers.Labels",
) -> "napari.types.LayerDataTuple":
    roi_corner_points = surface.metadata.get("roi_corner_points", None)

    output_name = derive_name(surface.name, "interpolated")

    params = {"roi_corner_points": roi_corner_points}
    interpolated = _run_and_record_action(
        func=fn.interpolate_gaps,
        inputs={"surface": asarray(surface.data)},
        input_layers={"surface": surface.name},
        output_layer=output_name,
        params=params,
    )

    layer_properties = {
        **copy_layer_properties(
            surface, include_opacity=True, include_contrast_limit=False
        ),
        # new layer_name
        "name": output_name,
    }

    return cast(
        "napari.types.LayerDataTuple", (interpolated, layer_properties, "labels")
    )
