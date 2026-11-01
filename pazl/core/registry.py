"""Element registry: every element type declares its params (with defaults and
descriptions), category, anchors it exposes, and a generator function."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from .geo import Manifold


@dataclass
class Anchor:
    """A frame where other elements attach.

    kind="face": local X along the face, Y = outward normal, Z = up, origin at the
                 bottom-left of the outer surface. w/h = face size, depth = wall thickness.
    kind="top":  origin at the footprint centre on top, X/Y horizontal, Z up.
                 footprint = polygon (local), height = height of the host below.
    kind="point": just a frame.
    """
    m: np.ndarray
    kind: str = "point"
    w: float = 0.0
    h: float = 0.0
    depth: float = 0.0
    footprint: list | None = None
    height: float = 0.0
    floors: int = 1
    floor_h: float = 3.0
    base: float = 0.0  # v of the first floor level on a face (plinth height)
    extra: dict = field(default_factory=dict)

    def to_json(self):
        d = {"kind": self.kind, "origin": [round(v, 3) for v in self.m[:3, 3]]}
        if self.kind == "face":
            d.update(w=round(self.w, 3), h=round(self.h, 3), depth=round(self.depth, 3),
                     normal=[round(v, 3) for v in self.m[:3, 1]], floors=self.floors,
                     floor_h=self.floor_h, base=self.base)
        if self.kind == "top":
            d.update(height=round(self.height, 3))
            if self.footprint:
                d["footprint"] = [[round(a, 3), round(b, 3)] for a, b in self.footprint]
        return d


@dataclass
class Part:
    solids: list = field(default_factory=list)      # [(Manifold, material)] in local coords
    cutters: list = field(default_factory=list)     # [(Manifold, material)] subtracted from host
    anchors: dict = field(default_factory=dict)     # name -> Anchor (local)
    children: list = field(default_factory=list)    # macro expansion: element dicts
    overlay: bool = False   # facade overlay: host-face cutters (windows) also cut this element
    notes: list = field(default_factory=list)

    def add(self, m: Manifold, mat: str):
        if m is not None and not m.is_empty():
            self.solids.append((m, mat))
        return self

    def cut(self, m: Manifold, mat: str = "@host"):
        if m is not None and not m.is_empty():
            self.cutters.append((m, mat))
        return self


@dataclass
class P:
    """Param spec."""
    default: Any
    desc: str = ""
    choices: list | None = None
    min: float | None = None
    max: float | None = None


@dataclass
class ElementType:
    name: str
    category: str
    desc: str
    params: dict[str, P]
    gen: Callable
    attach: str = "any"           # face | top | free | any
    anchors: str = ""             # human description of anchors exposed
    macro: bool = False
    title_ru: str = ""

    def schema(self, full=True):
        d = {"type": self.name, "category": self.category, "desc": self.desc, "attach": self.attach,
             "macro": self.macro}
        if self.title_ru:
            d["title_ru"] = self.title_ru
        if self.anchors:
            d["anchors"] = self.anchors
        if full:
            d["params"] = {k: {kk: vv for kk, vv in (("default", p.default), ("desc", p.desc),
                                                      ("choices", p.choices), ("min", p.min), ("max", p.max))
                               if vv is not None and vv != ""} for k, p in self.params.items()}
        return d


ELEMENTS: dict[str, ElementType] = {}


def element(name, category, desc, params, attach="any", anchors="", macro=False, title_ru=""):
    def deco(fn):
        ELEMENTS[name] = ElementType(name, category, desc, params, fn, attach, anchors, macro, title_ru)
        return fn
    return deco


class Ctx:
    """What a generator gets besides its params."""

    def __init__(self, detail: str, anchor: Anchor | None, style: dict, materials, eid: str, recipe=None):
        self.detail = detail
        self.anchor = anchor
        self.style = style
        self.materials = materials
        self.eid = eid
        self.recipe = recipe

    @property
    def low(self) -> bool:
        return self.detail == "lowpoly"

    def seg(self, r: float, lo=8, hi=64) -> int:
        """Circle segments for a radius depending on detail level."""
        if self.low:
            return max(6, min(lo + 4, int(6 + r * 4)))
        return int(max(16, min(hi, 24 + r * 24)))

    def mat(self, role_or_id: str) -> str:
        return self.materials.resolve(role_or_id, self.style)

    def art(self, kind: str, subject: str, color=None) -> str:
        """Register a unique material slot for artwork (mosaic, fresco, icon, stained glass)."""
        return self.materials.art_slot(self.eid, kind, subject, color)


def pct(v, total):
    """Accept numbers or '50%' strings."""
    if isinstance(v, str) and v.strip().endswith("%"):
        return float(v.strip()[:-1]) / 100.0 * total
    if v is None:
        return None
    return float(v)
