import yaml
from pathlib import Path
from .constants import BASE_LAYER_PLACEHOLDER


def _normalize_for_yaml(value):
    if isinstance(value, tuple):
        return [_normalize_for_yaml(item) for item in value]
    if isinstance(value, list):
        return [_normalize_for_yaml(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_for_yaml(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except (AttributeError, ValueError):
            pass
    return value


# TODO: make steps a TypedDict with function, input_layers, output_layer, params
class PipelineRecorder:
    def __init__(self) -> None:
        self.steps: list[dict] = []
        self.active: bool = False
        self._base_name: str | None = None

    def _templatize(self, name: str | None) -> str | None:
        """Replace the base layer name with the $base placeholder."""
        if name is None or self._base_name is None:
            return name
        if name == self._base_name:
            return BASE_LAYER_PLACEHOLDER
        prefix = f"{self._base_name}_"
        if name.startswith(prefix):
            return f"{BASE_LAYER_PLACEHOLDER}{name[len(self._base_name) :]}"
        return name

    def record(
        self,
        function: str,
        input_layers: dict[str, str | None],
        output_layer: str | None,
        params: dict,
    ) -> None:
        if not self.active:
            return

        if not self.steps:
            self._base_name = next(iter(input_layers.values()), None)

        self.steps.append(
            {
                "step": len(self.steps) + 1,
                "function": str(function),
                "input_layers": {
                    k: self._templatize(v) for k, v in input_layers.items()
                },
                "output_layer": self._templatize(output_layer),
                "params": _normalize_for_yaml(params),
            }
        )

    def clear(self) -> None:
        self.steps = []
        self._base_name = None

    def save(self, yaml_path: str | Path) -> None:
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"pipeline": self.steps},
                f,
                allow_unicode=True,
                sort_keys=False,
            )

    def load(self, yaml_path: str | Path) -> None:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.steps = data["pipeline"]
        self._base_name = None


recorder = PipelineRecorder()
