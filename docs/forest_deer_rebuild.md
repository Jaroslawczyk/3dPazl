# Forest deer 1:1 reference rebuild

Reference: `projects/refs/forest_deer/original.gltf` and its `scene.bin` / `textures/` files. The packed `original.glb` is the conversion used by the rebuild script and is kept beside the reference.

## Errors found in the first procedural draft

`scripts/glb_compare.py` compared 9,850 reference triangles with 5,544 draft triangles. The draft's normalized width/depth were 0.82/0.35 of its height; the reference is 0.79/0.40. Its silhouette was also off in these height bands:

| Height band | Reference width / height | Draft | Error | Fix |
| --- | ---: | ---: | --- | --- |
| 0.0–0.1 | 0.22 | 0.27 | Feet too wide | Preserve source hoof meshes |
| 0.2–0.3 | 0.77 | 0.28 | Thigh/knee outline too narrow | Preserve source leg pose and meshes |
| 0.4–0.5 | 0.68 | 0.82 | Upper legs too broad | Preserve source leg silhouette |
| 0.5–0.6 | 0.37 | 0.56 | Pelvis too broad | Preserve source torso and pelvis |
| 0.6–0.7 | 0.18 | 0.30 | Waist too broad | Preserve source torso silhouette |

The hand-built draft also had round ears and simpler surface detail than the original. Rather than claim an approximate recreation was 1:1, the final exporter preserves the user-provided mesh, UVs, materials, and textures and changes only the unit scale to a 2.22-unit height.

## Final comparison

`projects/лесной_олень/export/лесной_олень.glb` now has the same 9,850 triangles, normalized X/Y and Z/Y ratios (0.79 and 0.40), and all ten silhouette-band widths match the reference exactly. The final GLB was opened in 3dPazl and checked in the 3/4 view.

The built-in character generation and auto-rig calls returned `Method Not Allowed` in this session. The final asset therefore matches the supplied source but is not independently rigged or animated.
