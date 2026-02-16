# Python native imports
from typing import Literal, Callable
from functools import wraps, partial
import warnings
import traceback
from pathlib import Path
from dataclasses import dataclass, field

# Third party imports
import numpy as np
from qtpy.QtWidgets import QMessageBox
from magicgui.widgets import Container, PushButton, Label
import bio_oct
from bio_oct import Spacing, pipeline
import napari


@dataclass
class SessionState:
    pl = pipeline.BatchPipeline()
    affine: np.ndarray = field(default_factory=lambda: np.eye(4))
    spacing: Spacing | None = None
    source_dir: Path = Path.home()
    filename: str = "none"
    thresh_method: str = "none"
    substratum_coords: np.ndarray = field(default_factory=lambda: np.full((100, 100), 1))
    substratum_coords_nan: np.ndarray | None = None
    window_coords: np.ndarray = field(default_factory=lambda: np.full((100, 100), 0))
    valid_mask: np.ndarray | None = None
    reset_flag: bool = True

    def create_valid_mask(self, stack: np.ndarray) -> None:
        if self.window_coords is None or self.substratum_coords is None:
            raise ValueError(
                "Window or substratum coordinates are None in current session."
            )

        self.valid_mask = np.zeros_like(stack, dtype=bool)
        for b_scan in range(stack.shape[0]):
            for a_scan in range(stack.shape[2]):
                axial_min = self.window_coords[b_scan, a_scan]
                axial_max = self.substratum_coords[b_scan, a_scan]
                self.valid_mask[b_scan, axial_min:axial_max, a_scan] = True
    
    def draw_flat_surface(self, axial_idx: int, reference_stack: np.ndarray):
        b_scans, _, lateral = reference_stack.shape
        surface = vizualize_coords(
            stack=reference_stack,
            coord_array=np.full((b_scans, lateral), axial_idx, dtype=int)
        )
        return surface

    def reset(self):
        # function only works if default values are given for all class-variables
        for f in self.__dataclass_fields__:
            setattr(self, f, self.__dataclass_fields__[f].default)


def get_settings(
    settings_widgets: list[Callable], thresholding_method: str = "none"
) -> dict:
    all_settings = {}

    for widget in settings_widgets:
        widget_settings = {}
        # Die ursprünglichen Parameter stehen in __signature__.parameters
        for param in widget.__signature__.parameters:  # type: ignore
            if param == "viewer":
                continue

            func_name = widget.get_widget(param)  # type: ignore
            if func_name is None:
                continue

            setting_value = func_name.value
            if isinstance(setting_value, Path):
                continue

            widget_settings[param] = setting_value
        all_settings[widget.name or widget.__class__.__name__] = widget_settings  # type: ignore

    all_settings["thresholding_method"] = thresholding_method

    return all_settings


# Decorator for error handling in GUI functions
def gui_error_handler(func):
    """
    Decorator to handle errors and warnings in GUI functions.
    - Exceptions: show critical QMessageBox and stop execution.
    - Warnings: show warning QMessageBox but continue execution.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                tb = traceback.format_exc()

                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Error!")
                msg.setText(f"ERROR:\n {str(e)}")
                msg.setDetailedText(tb)
                msg.exec()

            all_warnings = [str(w.message) for w in caught_warnings]
            if all_warnings:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Warning!")
                msg.setText("Execution continued, but warnings occurred.")
                msg.setDetailedText("\n\n".join(all_warnings))
                msg.exec()

            return result

    return wrapper


# Create a label stack from coordinate array for visualization
def vizualize_coords(
    stack: np.ndarray, coord_array: np.ndarray, nan_coords: np.ndarray | None = None
) -> np.ndarray:
    label_stack = np.zeros_like(stack, dtype=np.uint8)
    b_scans, axial, lateral = stack.shape

    b_scans_idx, lateral_idx = np.meshgrid(
        np.arange(b_scans), np.arange(lateral), indexing="ij"
    )
    axial_idx = coord_array

    label_stack[b_scans_idx, axial_idx, lateral_idx] = 1

    if nan_coords is not None:
        nan_coords_3d = np.isnan(nan_coords)[:, np.newaxis, :]
        label_stack[:, :, :] = np.where(nan_coords_3d, 0, label_stack)

    return label_stack


# Updates or creates an image layer in the napari viewer
def update_layer(
    viewer: napari.Viewer,
    data: np.ndarray,
    affine,
    type: Literal["image", "labels"] = "image",
    metadata: dict | None = None,
    name: str = "",
    visible=True,
):
    if name in viewer.layers:
        layer = viewer.layers[name]
        layer.data = data
    else:
        if type == "labels":
            viewer.add_labels(data, affine=affine, name=name, visible=visible)
        else:
            viewer.add_image(data, affine=affine, name=name, visible=visible)

    if metadata is not None:
        layer = viewer.layers[name]
        layer.metadata = metadata

    return viewer.layers[name]


# Checks layer existence for certain functions as precondition
def layer_exists_check(viewer: napari.Viewer, layer_name: str):
    if layer_name not in viewer.layers:
        raise ValueError(f"Layer missing for this operation: {layer_name}.")

    return viewer.layers[layer_name]


## Create widget for thresholding function
def create_threshold_widget(
    viewer: napari.Viewer, thresholds: dict, stack: np.ndarray, state: SessionState
):
    container = Container()

    def apply_threshold(stack, viewer, method_name):
        binary = bio_oct.binarize.apply_threshold(stack, method_name)
        update_layer(
            viewer,
            binary,
            affine=state.affine,
            type="labels",
            name="binary",
        )

        state.thresh_method = method_name

    # Auto-threshold fields
    for name, value in thresholds.items():
        lbl = Label(value=f"{name}: {value:.2f}")
        btn = PushButton(text=f"Select {name}")

        btn.changed.connect(partial(apply_threshold, stack, viewer, name))

        container.append(lbl)  # type: ignore
        container.append(btn)  # type: ignore

    return container
