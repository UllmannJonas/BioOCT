from typing import Callable


REGISTRY: dict[str, Callable] = {}


def register(name: str):
    def decorator(func):
        REGISTRY[name] = func
        return func

    return decorator
