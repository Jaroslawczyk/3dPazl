"""Texture generators registry."""
from __future__ import annotations

from typing import Callable

from scripts.tile_gens import ground, metal, misc, road, roof, tech, wall, wood

GeneratorFn = Callable[[int, int, int], dict]

REGISTRY: dict[str, GeneratorFn] = {}
_REGISTRY = REGISTRY  # alias for make_tiles


def _reg(category: str, name: str, fn: GeneratorFn):
    _REGISTRY[f"{category}/{name}"] = fn


def get_generator(key: str) -> GeneratorFn:
    if key not in _REGISTRY:
        raise KeyError(key)
    return _REGISTRY[key]


def all_specs() -> list[tuple[str, str, float]]:
    """(category, name, tile_meters)"""
    specs: list[tuple[str, str, float]] = []
    for key in sorted(_REGISTRY):
        cat, name = key.split("/", 1)
        fn = _REGISTRY[key]
        tile_m = getattr(fn, "tile_meters", 1.0)
        specs.append((cat, name, tile_m))
    return specs


# register modules
wall.register(_reg)
roof.register(_reg)
ground.register(_reg)
road.register(_reg)
wood.register(_reg)
metal.register(_reg)
tech.register(_reg)
misc.register(_reg)
