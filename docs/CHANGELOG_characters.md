# Characters, Roblox and model-quality tools: what was built (2026-11-04, v0.58 - v0.72)

Read docs/MISTAKES.md for every mistake and its fix; this page is the inventory of what exists now.

## Viewer (web app)
- «Показ» menu: **Каркас** (white wire overlay for GLB views and workshops), **UV-чекер** (numbered grid, glTF orientation, magenta = no UVs), **Нормали** (vertex normals, follow animation), **Перспектива** on/off (off = flat, distortion-free view, same framing).
- **«✎ Пометки» → «📤 Агенту»**: click/drag on the model, add a note; saves `projects/marks/last.json` + `last.png` (points in file coordinates, part hit, note, camera, numbered marks on the picture). MCP `view_marks()` reads them.
- GLB viewer never shows a cached copy of a rebuilt file; it remembers which file is open.

## Model-quality tools (code, for any AI)
- `mesh_check` (MCP) / `scripts/mesh_check.py`: hole, poke_through, floating, flat_sheet, inside_out, mixed_winding, z_fighting, non_manifold, sliver, degenerate; each with `at` (metres, Y up, +Z front) and a plain place. Openings around limbs, seams of painted clothes, buried strand roots and float32 noise are not reported.
- `mesh_fix` (MCP) / `scripts/mesh_fix.py`: repairs the finished GLB in rounds (drop bad faces, close small holes with existing vertices, zip cracks, push hats/hair/clothes out of the body, fix extra faces on shared edges); keeps UV/skin/clips; keeps the best round; runs on every character export (<= 60k tris, `"no_fix": true` to skip).
- `scripts/glb_compare.py ref mine`: triangles, proportions, silhouette by height band.
- `pazl/core/retopo.py`: `Sampler` (exact closest point on a reference), `shrinkwrap`, `loft` + `ring` + `pack` (clean parts with an upright UV layout), `dome` (caps/beanies with a rolled brim), `lock` (solid hair locks), `sheet`, `card`, `prune`, `unwrap` (xatlas), `bake` (reference textures onto our UVs).
- MCP error when the running app is older than the code ("restart the app"); Codex config `[mcp_servers.pazl]`; agents must not build through the app's «ИИ» chat.

## Characters
- Block bodies built from boxes (`body.blocky_mesh`), preset `roblox` (R15 proportions); clothes painted on block bodies (`cloth.PAINT`), hair/hats capped at 1,200 tris.
- New kinds: `bird`, `hair_spiky` (roots on the scalp), `beanie_back`, `acc_head` / `acc_chest` (textured file that follows a bone), garment `print`.
- Recipe keys: `rest` / `rest_pose` (default pose in the file, bind stays T-pose), `labels` (block -> bone map), `no_fix`.
- Textured imported bodies keep their UVs and picture.
- Roblox export faces -Z; accessories exported with textures.

## 1:1 rebuild of a Roblox avatar (`scripts/rebuild_roblox_avatar.py`)
Original -> our frame -> R15-like parts measured on it (torso one piece neck->hips, head, arms/legs in 3 parts along their own axes) -> own UV layout -> original textures baked -> hair as solid locks, beanie as one dome with a rolled brim, pet wrapped and smooth -> T-pose bind with the measured pose as default -> character `galaxy_1to1` + Roblox export. About 4.7k triangles vs 5,078 in the original.

## Docs
- docs/QUICKSTART.md (start here), docs/MISTAKES.md (mistakes and fixes), docs/ROBLOX.md (characters, Roblox, 1:1 rebuild, hair/hat/torso rules), this file.
