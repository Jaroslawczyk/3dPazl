"""Build a compact, stylized low-poly forest deer character for 3dPazl."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh


OUT = Path(__file__).resolve().parents[1] / "projects" / "лесной_олень" / "export" / "лесной_олень.glb"

COLORS = {
    "fur": (68, 44, 37, 255),
    "fur_light": (84, 56, 47, 255),
    "fur_dark": (48, 34, 30, 255),
    "antler": (22, 25, 26, 255),
    "eye": (246, 244, 235, 255),
    "pupil": (16, 18, 19, 255),
    "glint": (255, 255, 255, 255),
    "muzzle": (188, 125, 105, 255),
    "ear": (135, 77, 81, 255),
    "mouth": (13, 15, 16, 255),
    "rim": (220, 157, 137, 255),
    "hoof": (29, 33, 34, 255),
}

scene = trimesh.Scene()


def add(mesh: trimesh.Trimesh, color: str, name: str) -> None:
    # The 3dPazl front view looks toward +Z; keep the face on that side.
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (0, 1, 0)))
    mesh.visual.material = trimesh.visual.material.PBRMaterial(
        name=color, baseColorFactor=COLORS[color], metallicFactor=0.0, roughnessFactor=0.92
    )
    scene.add_geometry(mesh, geom_name=name, node_name=name)


def ellipsoid(name: str, color: str, center, scale, subdivisions=1, rotation=None) -> None:
    mesh = trimesh.creation.icosphere(subdivisions=subdivisions, radius=1.0)
    mesh.apply_scale(scale)
    if rotation is not None:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(rotation[0], rotation[1]))
    mesh.apply_translation(center)
    add(mesh, color, name)


def frustum(name: str, color: str, start, end, r0: float, r1: float, sides=8) -> None:
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    axis = end - start
    length = np.linalg.norm(axis)
    if length < 1e-6:
        return
    unit = axis / length
    helper = np.array([0.0, 0.0, 1.0]) if abs(unit[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(unit, helper)
    u /= np.linalg.norm(u)
    v = np.cross(unit, u)
    verts = []
    for point, radius in ((start, r0), (end, r1)):
        for i in range(sides):
            angle = 2 * np.pi * i / sides
            verts.append(point + radius * (np.cos(angle) * u + np.sin(angle) * v))
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.extend(((i, j, sides + j), (i, sides + j, sides + i)))
    for i in range(1, sides - 1):
        faces.append((0, i + 1, i))
        faces.append((sides, sides + i, sides + i + 1))
    add(trimesh.Trimesh(vertices=verts, faces=faces, process=True), color, name)


def link(name, color, a, b, radius_a, radius_b, sides=9):
    frustum(name, color, a, b, radius_a, radius_b, sides)


# Hooves and long, bent legs.
for side in (-1, 1):
    x = side
    ellipsoid(f"hoof_{x}_left", "hoof", (x * 0.19 - 0.039, 0.065, -0.035), (0.067, 0.067, 0.145))
    ellipsoid(f"hoof_{x}_right", "hoof", (x * 0.19 + 0.039, 0.065, -0.035), (0.067, 0.067, 0.145))
    link(f"shin_{x}", "fur_dark", (x * 0.19, 0.13, 0.005), (x * 0.145, 0.43, 0.06), 0.055, 0.068)
    ellipsoid(f"knee_{x}", "fur", (x * 0.145, 0.46, 0.055), (0.105, 0.12, 0.11))
    link(f"thigh_{x}", "fur", (x * 0.145, 0.48, 0.045), (x * 0.17, 0.79, 0.015), 0.105, 0.145)
    ellipsoid(f"hip_{x}", "fur_light", (x * 0.15, 0.78, 0.0), (0.15, 0.19, 0.145))
    # A few short fur points break the smooth silhouette at the haunch.
    frustum(f"haunch_tuft_{x}", "fur_dark", (x * 0.25, 0.60, -0.01), (x * 0.29, 0.53, -0.015), 0.07, 0.002, 6)

# Torso, chest, neck and tufts.
ellipsoid("pelvis", "fur_dark", (0, 0.86, 0.015), (0.225, 0.19, 0.16), subdivisions=2)
ellipsoid("torso", "fur", (0, 1.12, 0.0), (0.235, 0.32, 0.16), subdivisions=2)
ellipsoid("chest", "fur_light", (0, 1.30, -0.012), (0.28, 0.17, 0.17), subdivisions=2)
for i, (x, y, z, dx, dy) in enumerate([
    (-0.20, 1.26, -0.015, -0.08, -0.11), (0.20, 1.26, -0.015, 0.08, -0.11),
    (-0.19, 1.08, -0.015, -0.05, -0.12), (0.19, 1.08, -0.015, 0.05, -0.12),
    (-0.16, 0.96, -0.01, -0.035, -0.10), (0.16, 0.96, -0.01, 0.035, -0.10),
]):
    frustum(f"chest_fur_{i}", "fur_dark", (x, y, z), (x + dx, y + dy, z - 0.008), 0.045, 0.001, 5)
link("neck", "fur_dark", (0, 1.31, 0.045), (0, 1.52, 0.035), 0.115, 0.105)

# Arms angle outward and slightly downward, with dark hands and tapered claws.
for side in (-1, 1):
    shoulder = (side * 0.22, 1.30, 0.01)
    elbow = (side * 0.53, 1.16, -0.005)
    wrist = (side * 0.77, 0.99, -0.025)
    palm = (side * 0.84, 0.94, -0.035)
    ellipsoid(f"shoulder_{side}", "fur_light", shoulder, (0.145, 0.16, 0.13))
    link(f"upper_arm_{side}", "fur", shoulder, elbow, 0.105, 0.085)
    ellipsoid(f"elbow_{side}", "fur_dark", elbow, (0.09, 0.09, 0.09))
    link(f"forearm_{side}", "fur_dark", elbow, wrist, 0.075, 0.055)
    ellipsoid(f"palm_{side}", "hoof", palm, (0.075, 0.105, 0.055))
    for digit in (-1, 0, 1):
        sx = side * (0.81 + (0.045 if digit == 0 else 0.0)) + digit * 0.039
        sy = 0.91 - (0.015 if digit == 0 else 0.0)
        ex = sx + side * (0.018 if digit != 0 else 0.04)
        ey = sy - (0.12 if digit == 0 else 0.095)
        frustum(f"claw_{side}_{digit}", "antler", (sx, sy, -0.055), (ex, ey, -0.065), 0.027, 0.001, 6)

# Head, expressive eyes, muzzle, mouth and inner ears.
ellipsoid("head", "fur", (0, 1.66, 0.015), (0.255, 0.265, 0.22), subdivisions=2)
for side in (-1, 1):
    ellipsoid(f"ear_{side}", "fur_dark", (side * 0.275, 1.75, 0.025), (0.125, 0.16, 0.075), rotation=(side * 0.36, (0, 0, 1)))
    ellipsoid(f"ear_inner_{side}", "ear", (side * 0.281, 1.755, -0.040), (0.075, 0.105, 0.025), rotation=(side * 0.36, (0, 0, 1)))
    ellipsoid(f"eye_white_{side}", "eye", (side * 0.105, 1.72, -0.176), (0.092, 0.112, 0.066), subdivisions=2)
    ellipsoid(f"eye_pupil_{side}", "pupil", (side * 0.105, 1.715, -0.232), (0.043, 0.062, 0.023))
    ellipsoid(f"eye_glint_{side}", "glint", (side * 0.119, 1.748, -0.252), (0.014, 0.020, 0.009), subdivisions=1)
ellipsoid("muzzle", "muzzle", (0, 1.605, -0.213), (0.165, 0.125, 0.16), subdivisions=2)
ellipsoid("nose", "pupil", (0, 1.645, -0.348), (0.051, 0.043, 0.038))
ellipsoid("open_mouth", "mouth", (0, 1.505, -0.199), (0.071, 0.145, 0.035), subdivisions=2)
mouth_rim = trimesh.creation.torus(major_radius=0.078, minor_radius=0.012, major_sections=16, minor_sections=5)
mouth_rim.apply_scale((0.92, 1.72, 0.52))
mouth_rim.apply_translation((0, 1.505, -0.233))
add(mouth_rim, "rim", "mouth_rim")

# Tall branched antlers, mirrored and tapered to fine points.
for side in (-1, 1):
    p0 = (side * 0.13, 1.84, 0.015)
    p1 = (side * 0.21, 1.98, 0.02)
    p2 = (side * 0.34, 2.04, 0.018)
    p3 = (side * 0.40, 2.19, 0.01)
    link(f"antler_main_1_{side}", "antler", p0, p1, 0.044, 0.036, 7)
    link(f"antler_main_2_{side}", "antler", p1, p2, 0.036, 0.030, 7)
    link(f"antler_main_3_{side}", "antler", p2, p3, 0.030, 0.002, 7)
    # Outer tine.
    link(f"antler_outer_1_{side}", "antler", (side * 0.27, 2.01, 0.018), (side * 0.38, 2.08, 0.005), 0.027, 0.021, 7)
    link(f"antler_outer_2_{side}", "antler", (side * 0.38, 2.08, 0.005), (side * 0.47, 2.20, -0.005), 0.021, 0.002, 7)
    # Two inner prongs, one shorter and one tall.
    link(f"antler_inner_short_{side}", "antler", (side * 0.22, 1.98, 0.02), (side * 0.18, 2.14, 0.015), 0.028, 0.002, 7)
    link(f"antler_inner_tall_{side}", "antler", (side * 0.32, 2.03, 0.016), (side * 0.29, 2.22, 0.005), 0.024, 0.002, 7)

# Short pointed tail angles back and upward.
ellipsoid("tail_base", "fur_dark", (0, 0.79, 0.16), (0.09, 0.09, 0.10))
link("tail", "fur", (0, 0.79, 0.19), (0, 0.89, 0.39), 0.085, 0.002, 7)

OUT.parent.mkdir(parents=True, exist_ok=True)
scene.export(OUT, file_type="glb")
loaded = trimesh.load(OUT, force="scene")
triangles = sum(len(mesh.faces) for mesh in loaded.geometry.values())
print(f"Wrote {OUT} ({triangles} triangles, height 2.22 units)")
