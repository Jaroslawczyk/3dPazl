# Mistakes already made and how to avoid them (read before building a model)

Every line here cost the user a round of "это криво". Check your plan against it first.

## Process
| Mistake | Fix / rule |
|---|---|
| Built a look-alike with generators when the user wanted "1 к 1" | Rebuild from the user's original with `pazl/core/retopo.py` + bake the user's textures (`scripts/rebuild_roblox_avatar.py` is the worked example). Never copy the original mesh. |
| Showed results without looking for defects | Run `mesh_check` (MCP) / `scripts/mesh_check.py`, then `mesh_fix`, then look in the app next to the original, THEN show. |
| Judged from one camera angle | Check front, side, back, below the hat, close-ups of joints; with «Каркас» and «UV-чекер». |
| Drove the app's own «ИИ» chat / clicked the UI to build | Use the MCP tools or the Python API; browser only to show. |
| Stale app server (old code) gave "Method Not Allowed" | Restart `.venv/Scripts/python.exe -m pazl.server`; MCP now says so itself. |
| Drew textures myself | Don't: textures come from the user or CC0 downloads. Focus on geometry, rigs, animation. |
| Screenshot right after a change showed the previous frame / `zoom` stale | `invalidate(true)` twice with pauses; take the screenshot twice. |
| Browser cached an old GLB after a rebuild | Fixed: viewer fetches with `cache: 'no-store'`. Don't add `?r=N` to paths. |
| The user's «Срез» (clip) slider hid the head; «Перспектива» off made the view look empty | Check `#rngClip` and `#chkPersp` before concluding a model is missing; restore the user's values after. |
| Another long job was still rewriting the file while I checked it | Wait for the background job's notification before checking/committing. |

## Geometry
| Mistake | Fix / rule |
|---|---|
| 45k triangles (x9 the original): garments as 3D shells | Block bodies: clothes painted on the body (`cloth.PAINT`); budgets in docs/QUICKSTART.md. |
| Body from a remeshed field: blobby, too heavy | Block bodies straight from boxes / R15 lofts measured on the reference (`r15_body`). |
| Per-piece shrinkwrap: boxes rotated at random angles ("криво и косо") | Build each R15 part as a loft along its limb axis (`retopo.loft`), joints from the reference's joint discs. |
| Lower torso wider/shifted, then still a separate block with a step: shirt "split in two, crooked" | The torso is ONE loft from the neck to the bottom of the lower torso (one surface, one UV strip, bone `chest`); never build R15 Upper/LowerTorso as two blocks. |
| Arms in T-pose in a static file | Bind stays T-pose; the measured pose is the default node rotation (`rest_pose`). |
| Model faced +Z in Roblox (they face -Z) | `roblox_export` turns model and accessories. |
| Hat clipping into the head / hair | `push_out_faces`; weld vertices BEFORE pushing (a shared vertex pushed on one side tears the seam). |
| Beanie: brim ring separate from the dome, gap showed the head | `retopo.dome` = one loft along the hat axis; merge same-coloured brim layers (`rebuild(color=...)`, inside > 40% of the dome box). |
| Beanie bottom: thin open edge showing the inside | Straight band + rolled brim turning inward (`dome`, 12% thick). |
| Hair: flat ribbons, cards in the air, through the head | Strands = closed convex-hull locks (`retopo.lock`) at the original place; roots buried in the scalp; never push/cut/collapse small closed pieces (`meshcheck.lock_faces`). |
| Curved hair shells made flat → bare top of the head | `is_curved`: wrap bent shells, prune bridges (`prune`). |
| Open pieces closed by an icosphere across the head | Only real caps become domes (`is_cap`: opening as wide as the piece); bulky pieces stay closed. |
| Bird feet squashed by push-out | Pets stand on the highest block under them, slightly above. |
| Glb metallic default 1 → model rendered dark | Always write `metallicFactor = 0`. |
| UV islands mirrored (xatlas v up vs glTF v down) | Flip v from xatlas; app's UV checker uses `flipY = false`. |
| Original looks brighter | It is unlit (`KHR_materials_unlit`); ours is lit like Roblox. Not a texture error. |

## Checker / fixer pitfalls (in the tools themselves)
| Mistake | Fix |
|---|---|
| `trimesh.split()` silently FILLED holes, so small holes were never reported | Always `split(only_watertight=False, repair=False)`. |
| Welding at 1e-8 reported float32 noise as holes | Weld at 1 micron (`digits_vertex=6`). |
| Seams between painted clothes reported as holes | Borders shared with another part are seams. |
| Hair card roots reported as poke-through | Open strands and small closed locks are skipped; only shallow dips count. |
| Cleaning cut long faces of locks → holes | Never cut / collapse small closed pieces; only needles on an open border go. |
| mesh_fix oscillated and made things worse | It keeps the best round and never returns a worse file. |
| Auto-fix crashed an export (unreadable vertex colours) | Export restores the file and reports `mesh_fix` skipped. |
| Rim broken into arcs by touching strands reported as holes | Known false positive: judge by eye; the rim is under the hat. |

## Tools (what to reach for)
| Tool | Use |
|---|---|
| `mesh_check(path)` / `scripts/mesh_check.py` | holes, poke_through, floating, flat_sheet, inside_out, mixed_winding, z_fighting, non_manifold, sliver, degenerate - each with `at` (metres, Y up, +Z front) and a plain place |
| `mesh_fix(path)` / `scripts/mesh_fix.py` | repairs the finished GLB (keeps UV/skin/clips); runs automatically on character export |
| `view_marks()` | points the user clicked in the app («✎ Пометки» → «📤 Агенту»): coordinates, part, note, screenshot |
| `scripts/glb_compare.py ref mine` | triangles, proportions, silhouette by height |
| `scripts/rebuild_roblox_avatar.py` | 1:1 rebuild of a Roblox avatar with the original textures |
| `pazl/core/retopo.py` | `loft`, `pack`, `dome`, `lock`, `sheet`, `shrinkwrap`, `bake`, `Sampler.project` |
| App «Показ» | Каркас, UV-чекер, Нормали, Перспектива on/off |
