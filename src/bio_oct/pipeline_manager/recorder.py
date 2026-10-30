from pathlib import Path
from typing import Any

import yaml

_STEP_FIELDS = {
    "step",
    "function",
    "input_layers",
    "output_layer",
    "params",
}


def _validate_pipeline(data: Any) -> list[dict]:
    if not isinstance(data, dict):
        raise TypeError("Invalid pipeline YAML: root must be a mapping")
    if "pipeline" not in data:
        raise ValueError("Invalid pipeline YAML: missing required 'pipeline' field")

    steps = data["pipeline"]
    if not isinstance(steps, list):
        raise TypeError("Invalid pipeline YAML: 'pipeline' must be a list")

    validated_steps: list[dict] = []
    for step_nr, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise TypeError(f"Invalid pipeline step {step_nr}: must be a mapping")

        unknown_fields = [key for key in step if key not in _STEP_FIELDS]
        if unknown_fields:
            unknown = ", ".join(repr(key) for key in sorted(unknown_fields))
            raise ValueError(f"Invalid pipeline step {step_nr}: unknown key {unknown}")

        missing_fields = [field for field in _STEP_FIELDS if field not in step]
        if missing_fields:
            missing = ", ".join(repr(field) for field in sorted(missing_fields))
            raise ValueError(
                f"Invalid pipeline step {step_nr}: missing required key {missing}"
            )

        if type(step["step"]) is not int:
            raise TypeError(
                f"Invalid pipeline step {step_nr}: 'step' must be an integer"
            )
        if not isinstance(step["function"], str):
            raise TypeError(
                f"Invalid pipeline step {step_nr}: 'function' must be a string"
            )

        input_layers = step["input_layers"]
        if not isinstance(input_layers, dict):
            raise TypeError(
                f"Invalid pipeline step {step_nr}: 'input_layers' must be a mapping"
            )
        for argument, layer_reference in input_layers.items():
            if not isinstance(argument, str):
                raise TypeError(
                    f"Invalid pipeline step {step_nr}: "
                    "input layer argument names must be strings"
                )
            if layer_reference is not None and not isinstance(layer_reference, str):
                raise TypeError(
                    f"Invalid pipeline step {step_nr}: input layer reference "
                    f"{argument!r} must be a string or null"
                )

        output_layer = step["output_layer"]
        if output_layer is not None and not isinstance(output_layer, str):
            raise TypeError(
                f"Invalid pipeline step {step_nr}: "
                "'output_layer' must be a string or null"
            )

        params = step["params"]
        if not isinstance(params, dict):
            raise TypeError(
                f"Invalid pipeline step {step_nr}: 'params' must be a mapping"
            )
        if any(not isinstance(name, str) for name in params):
            raise TypeError(
                f"Invalid pipeline step {step_nr}: parameter names must be strings"
            )

        validated_steps.append(step)

    return validated_steps


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
        base = "$base"

        if name is None or self._base_name is None:
            return name
        if name == self._base_name:
            return base
        prefix = f"{self._base_name}_"
        if name.startswith(prefix):
            return f"{base}{name[len(self._base_name) :]}"
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
        steps = _validate_pipeline(data)
        self.steps = steps
        self._base_name = None


recorder = PipelineRecorder()
