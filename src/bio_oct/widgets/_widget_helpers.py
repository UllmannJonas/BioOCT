from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..pipeline_manager.panel import get_panel
from ..pipeline_manager.recorder import recorder


def _run_and_record_action(
    func: Callable[..., Any],
    inputs: dict[str, Any],
    input_layers: dict[str, str | None],
    output_layer: str | None,
    params: dict[str, Any],
    resolve_path: Callable[[str], Path] | None = None,
) -> Any:
    """Run and record an action; inputs = runtime-only kwargs, params = recorded kwargs."""
    run_params = dict(params)
    if resolve_path is not None:
        run_params["path"] = resolve_path(run_params.pop("output_filename"))
    result = func(**inputs, **run_params)
    recorder.record(
        function=func.__name__,
        input_layers=input_layers,
        output_layer=output_layer,
        params=params,
    )
    panel = get_panel()
    if panel is not None:
        panel.refresh()
    return result


def _get_napari_image_class():
    import napari.layers

    return napari.layers.Image
