import yaml
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QCheckBox,
    QFileDialog,
    QComboBox,
    QLabel,
    QLineEdit,
    QGroupBox,
    QMessageBox,
)
from qtpy.QtGui import QFont
from .recorder import recorder

if TYPE_CHECKING:
    import napari.viewer


def get_panel():
    return panel


class PipelineManager(QWidget):
    def __init__(self, viewer: "napari.viewer.Viewer", parent=None):
        super().__init__(parent)
        self.viewer = viewer
        global panel
        panel = self

        # --- Record Toggle ---
        self.record_toggle = QCheckBox("Record Pipeline")
        self.record_toggle.toggled.connect(self._on_toggle)

        # --- YAML Live-View ---
        self.text_view = QPlainTextEdit()
        self.text_view.setFont(QFont("Courier New", 8))
        self.text_view.setReadOnly(True)

        # --- IO Buttons ---
        self.save_btn = QPushButton("💾 Save")
        self.load_btn = QPushButton("📂 Load")
        self.save_btn.clicked.connect(self._on_save)
        self.load_btn.clicked.connect(self._on_load)

        io_row = QHBoxLayout()
        io_row.addWidget(self.load_btn)
        io_row.addWidget(self.save_btn)

        # --- Edit Buttons ---
        self.pop_btn = QPushButton("↩ Delete Last")
        self.clear_btn = QPushButton("🗑 Clear")
        self.pop_btn.clicked.connect(self._on_pop)
        self.clear_btn.clicked.connect(self._on_clear)

        edit_row = QHBoxLayout()
        edit_row.addWidget(self.pop_btn)
        edit_row.addWidget(self.clear_btn)

        # --- Single Replay ---
        single_group = QGroupBox("Single Replay")
        single_layout = QVBoxLayout()

        self.layer_label = QLabel("Apply to:")
        self.layer_combo = QComboBox()
        self.layer_combo.setMinimumWidth(160)
        self._refresh_layer_combo()
        # Keep combo up to date when new layers are added/removed in viewer
        viewer.layers.events.inserted.connect(self._refresh_layer_combo)
        viewer.layers.events.removed.connect(self._refresh_layer_combo)

        layer_row = QHBoxLayout()
        layer_row.addWidget(self.layer_label)
        layer_row.addWidget(self.layer_combo, stretch=1)

        self.replay_single_btn = QPushButton("▶ Replay Single")
        self.replay_single_btn.clicked.connect(self._on_replay_single)

        single_layout.addLayout(layer_row)
        single_layout.addWidget(self.replay_single_btn)
        single_group.setLayout(single_layout)

        # --- Batch Replay ---
        batch_group = QGroupBox("Batch Replay")
        batch_layout = QVBoxLayout()

        self.batch_folder_edit = QLineEdit()
        self.batch_folder_edit.setPlaceholderText("No folder selected...")
        self.batch_folder_edit.setReadOnly(True)
        self.batch_browse_btn = QPushButton("📁 Browse")
        self.batch_browse_btn.clicked.connect(self._on_batch_browse)

        folder_row = QHBoxLayout()
        folder_row.addWidget(self.batch_folder_edit, stretch=1)
        folder_row.addWidget(self.batch_browse_btn)

        self.replay_batch_btn = QPushButton("▶▶ Replay Batch")
        self.replay_batch_btn.clicked.connect(self._on_replay_batch)

        # --- Optional Replay Output Folder ---
        output_group = QGroupBox("Replay Output")
        output_layout = QVBoxLayout()

        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Dataset source folder (default)")
        self.output_folder_edit.setReadOnly(True)

        self.output_folder_browse_btn = QPushButton("📁 Browse")
        self.output_folder_browse_btn.clicked.connect(self._on_output_folder_browse)
        self.output_folder_clear_btn = QPushButton("Use default")
        self.output_folder_clear_btn.clicked.connect(self.output_folder_edit.clear)
        self.output_folder_clear_btn.setEnabled(False)
        self.output_folder_edit.textChanged.connect(
            lambda text: self.output_folder_clear_btn.setEnabled(bool(text))
        )

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.output_folder_browse_btn)
        btn_row.addWidget(self.output_folder_clear_btn)

        output_layout.addWidget(self.output_folder_edit)
        output_layout.addLayout(btn_row)
        output_group.setLayout(output_layout)

        batch_layout.addLayout(folder_row)
        batch_layout.addWidget(self.replay_batch_btn)
        batch_group.setLayout(batch_layout)

        # --- Full Layout ---
        layout = QVBoxLayout()
        layout.addWidget(self.record_toggle)
        layout.addWidget(self.text_view)
        layout.addLayout(io_row)
        layout.addLayout(edit_row)
        layout.addWidget(output_group)
        layout.addWidget(single_group)
        layout.addWidget(batch_group)
        self.setLayout(layout)

    # --- Functions ---
    def _refresh_layer_combo(self, _event=None):
        """Put all current viewer layer names in Dropdown Menu."""
        current = self.layer_combo.currentText()
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for layer in self.viewer.layers:
            self.layer_combo.addItem(layer.name)
        # Restore previous selection if still available
        idx = self.layer_combo.findText(current)
        if idx >= 0:
            self.layer_combo.setCurrentIndex(idx)
        self.layer_combo.blockSignals(False)

    def _on_toggle(self, checked: bool):
        recorder.active = checked

    def refresh(self):
        self.text_view.setPlainText(
            yaml.dump(
                {"pipeline": recorder.steps},
                allow_unicode=True,
                sort_keys=False,
            )
        )

    def _on_pop(self):
        if recorder.steps:
            recorder.steps.pop()
            for i, step in enumerate(recorder.steps):
                step["step"] = i + 1
        self.refresh()

    def _on_clear(self):
        recorder.clear()
        self.refresh()

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Pipeline", "", "YAML (*.yaml)"
        )
        if path:
            recorder.save(path)

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Pipeline", "", "YAML (*.yaml)"
        )
        if path:
            recorder.load(path)
            self.refresh()

    def _on_replay_single(self):
        from .replay import replay_pipeline

        base_layer = self.layer_combo.currentText() or None
        try:
            replay_pipeline(
                recorder,
                self.viewer,
                base_layer_name=base_layer,
                output_folder=self._selected_output_folder(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid output folder", str(exc))

    def _on_batch_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with .oct Files")
        if folder:
            self.batch_folder_edit.setText(folder)

    def _on_output_folder_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Replay Output Folder")
        if folder:
            self.output_folder_edit.setText(folder)

    def _selected_output_folder(self) -> Path | None:
        folder = self.output_folder_edit.text().strip()
        return Path(folder) if folder else None

    def _on_replay_batch(self):
        from .replay import replay_on_batch

        folder_str = self.batch_folder_edit.text().strip()
        if not folder_str:
            return
        try:
            replay_on_batch(
                recorder,
                self.viewer,
                Path(folder_str),
                output_folder=self._selected_output_folder(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid output folder", str(exc))


panel = None
