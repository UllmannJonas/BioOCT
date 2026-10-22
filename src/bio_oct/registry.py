from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

OutputType = Literal["image", "labels"] | None


@dataclass(frozen=True)
class FunctionSpec:
    func: Callable[..., Any]
    output: OutputType
    context: tuple[str, ...] = ()
    after: Callable[..., Any] | None = None


def store_roi_metadata(layer: Any, params: dict[str, Any]) -> None:
    layer.metadata["roi_corner_points"] = params["roi_corner_points"]


REGISTRY: dict[str, FunctionSpec] = {}


def register(
    *,
    output: OutputType,
    context: tuple[str, ...] = (),
    after: Callable[..., Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRY[func.__name__] = FunctionSpec(
            func=func,
            output=output,
            context=tuple(context),
            after=after,
        )
        return func

    return decorator
