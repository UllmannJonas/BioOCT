from pathlib import Path
from typing import Any


def resolve_output_path(
    filename: str,
    layer: Any,
    output_folder: Path | None = None,
) -> Path:
    """Resolve a filename template using the layer name and output directory."""
    metadata = getattr(layer, "metadata", {})
    destination = (
        Path(output_folder)
        if output_folder is not None
        else Path(metadata.get("source_dir", Path.home()))
    )
    layer_name = layer.name if hasattr(layer, "name") else "unknown_layer"
    return destination / filename.replace("{input_layer}", layer_name)
