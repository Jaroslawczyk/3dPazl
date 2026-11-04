"""Build a 1:1-size GLB from the user's supplied forest-deer reference."""

from pathlib import Path

import trimesh


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "projects" / "refs" / "forest_deer" / "original.glb"
OUTPUT = ROOT / "projects" / "лесной_олень" / "export" / "лесной_олень.glb"
TARGET_HEIGHT = 2.22


scene = trimesh.load(SOURCE, force="scene")
if not len(scene.geometry):
    raise RuntimeError(f"Reference has no mesh geometry: {SOURCE}")

# Preserve the original meshes, UVs, materials, and proportions; normalize only units.
bounds = scene.bounds
height = float(bounds[1, 1] - bounds[0, 1])
if height <= 0:
    raise RuntimeError(f"Invalid reference height: {height}")
scale = TARGET_HEIGHT / height
scene.apply_transform(trimesh.transformations.scale_and_translate(scale, [0, 0, 0]))
scene.apply_transform(trimesh.transformations.translation_matrix([0, -scene.bounds[0, 1], 0]))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
scene.export(OUTPUT, file_type="glb")

check = trimesh.load(OUTPUT, force="scene")
triangles = sum(len(mesh.faces) for mesh in check.geometry.values())
print(f"Wrote {OUTPUT}: {triangles:,} triangles, height {check.bounds[1, 1] - check.bounds[0, 1]:.3f}")
