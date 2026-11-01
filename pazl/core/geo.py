"""Geometry helpers on top of manifold3d. Z is up, units are meters.

Every solid that reaches the builder is tagged with a material (and the element
that produced it) through `tag()`. The tag survives boolean operations because
manifold keeps per-triangle provenance (original ids).
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np
from manifold3d import CrossSection, FillRule, JoinType, Manifold, OpType

M = Manifold
CS = CrossSection

# original_id -> (material, element_id)
REGISTRY: dict[int, tuple[str, str]] = {}
_current_elem = ["?"]


def set_current_element(eid: str) -> None:
    _current_elem[0] = eid


def tag(m: Manifold, mat: str) -> Manifold:
    """Mark a solid with a material; returns a new original solid."""
    m2 = m.as_original()
    REGISTRY[m2.original_id()] = (mat, _current_elem[0])
    return m2


def info(orig_id: int) -> tuple[str, str]:
    return REGISTRY.get(orig_id, ("default", "?"))


# ---------------------------------------------------------------- matrices
def mat_t(x=0.0, y=0.0, z=0.0) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def mat_rz(deg: float) -> np.ndarray:
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


def mat_rx(deg: float) -> np.ndarray:
    a = math.radians(deg)
    m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


def mat_ry(deg: float) -> np.ndarray:
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    return m


def mat_frame(origin, xaxis, yaxis, zaxis) -> np.ndarray:
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = xaxis, yaxis, zaxis, origin
    return m


def xf(m: Manifold, mat4: np.ndarray) -> Manifold:
    return m.transform(np.asarray(mat4, dtype=float)[:3, :4])


# ---------------------------------------------------------------- 2D
def ccw(pts: Sequence[Sequence[float]]) -> list[tuple[float, float]]:
    pts = [(float(p[0]), float(p[1])) for p in pts]
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return pts if a > 0 else pts[::-1]


def poly(pts) -> CrossSection:
    return CrossSection([ccw(pts)], FillRule.NonZero)


def rect2(w, h, cx=0.0, y0=0.0) -> CrossSection:
    return poly([(cx - w / 2, y0), (cx + w / 2, y0), (cx + w / 2, y0 + h), (cx - w / 2, y0 + h)])


def circle2(r, seg, cx=0.0, cy=0.0) -> CrossSection:
    return CrossSection.circle(r, seg).translate((cx, cy))


def offset2(cs: CrossSection, d: float, round_=False) -> CrossSection:
    return cs.offset(d, JoinType.Round if round_ else JoinType.Miter, 2.0, 16)


def union_cs(items) -> CrossSection:
    items = [c for c in items if c is not None and not c.is_empty()]
    return CrossSection.batch_boolean(items, OpType.Add) if len(items) > 1 else items[0]


def arc_pts(cx, cy, r, a0, a1, n) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


# ---------------------------------------------------------------- 3D primitives
def box(x0, y0, z0, x1, y1, z1) -> Manifold:
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def boxc(w, d, h, cx=0.0, cy=0.0, z0=0.0) -> Manifold:
    return box(cx - w / 2, cy - d / 2, z0, cx + w / 2, cy + d / 2, z0 + h)


def cyl(r, h, seg, z0=0.0, r2=None, cx=0.0, cy=0.0) -> Manifold:
    return M.cylinder(h, r, r if r2 is None else r2, seg).translate([cx, cy, z0])


def sphere(r, seg, c=(0, 0, 0)) -> Manifold:
    return M.sphere(r, seg).translate(list(c))


def extrude(cs: CrossSection, h: float, z0=0.0, scale_top=(1.0, 1.0)) -> Manifold:
    return M.extrude(cs, h, 0, 0.0, scale_top).translate([0, 0, z0])


def prism_xz(cs: CrossSection, y0: float, y1: float) -> Manifold:
    """2D shape drawn in (x, z) extruded along Y from y0 to y1."""
    return M.extrude(cs, y1 - y0).rotate([90, 0, 0]).translate([0, y1, 0])


def prism_yz(cs: CrossSection, x0: float, x1: float) -> Manifold:
    """2D shape drawn in (y, z) extruded along X from x0 to x1."""
    return prism_xz(cs, -x1, -x0).rotate([0, 0, 90])


def revolve(profile: Sequence[Sequence[float]], seg: int) -> Manifold:
    """profile: (r, z) points, outer contour; axis points (r=0) close it."""
    pts = [(max(0.0, float(r)), float(z)) for r, z in profile]
    return M.revolve(poly(pts), seg)


def hull(points: Iterable[Sequence[float]]) -> Manifold:
    return M.hull_points([list(map(float, p)) for p in points])


def beam(p0, p1, w, h) -> Manifold:
    """Rectangular beam between two 3D points (w horizontal, h along the up-ish normal)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return M()
    x = d / L
    up = np.array([0, 0, 1.0]) if abs(x[2]) < 0.95 else np.array([0, 1.0, 0])
    y = np.cross(up, x)
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    b = box(0, -w / 2, -h / 2, L, w / 2, h / 2)
    return xf(b, mat_frame(p0, x, y, z))


def rod(p0, p1, r, seg) -> Manifold:
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    if L < 1e-6:
        return M()
    z = d / L
    a = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(a, z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return xf(M.cylinder(L, r, r, seg), mat_frame(p0, x, y, z))


def union(parts: list[Manifold]) -> Manifold:
    parts = [p for p in parts if p is not None and not p.is_empty()]
    if not parts:
        return M()
    if len(parts) == 1:
        return parts[0]
    return M.batch_boolean(parts, OpType.Add)


def subtract(a: Manifold, cutters: list[Manifold]) -> Manifold:
    cutters = [c for c in cutters if c is not None and not c.is_empty()]
    if not cutters:
        return a
    return a - union(cutters)


def bbox(m: Manifold):
    b = m.bounding_box()
    return np.array(b[:3]), np.array(b[3:])
