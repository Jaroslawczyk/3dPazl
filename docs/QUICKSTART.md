# 3dPazl in 2 minutes: read this first, then only the one doc your task needs

The goal: start working at once, without exploring the repo. Everything below was learned the expensive way.

## Where things are
| Task | Code | Doc |
|---|---|---|
| Buildings (recipes, MCP tools) | `pazl/core/elements/`, `pazl/mcp.py` | docs/AI_GUIDE.md |
| Vehicles, low-poly craft | `pazl/core/vehicles/` | docs/model_craft.md |
| Characters, clothes, Roblox | `pazl/core/chars/` (body.py bodies, cloth.py garments, `__init__.py` assembly), `pazl/core/roblox.py` | docs/ROBLOX.md |
| Skins (tileable textures) | `pazl/core/skins.py` | docs/ROBLOX.md |
| Rig, animation | `pazl/core/rig/` | docs/AI_GUIDE.md |
| Web app | `web/app.js` (viewport), `web/ws/*.js` (workshops), `web/debugview.js` (UV checker, normals, wireframe) | |
| Server API | `pazl/server/workshops.py` (`/api/ws/...`) | |

## Build without the server (fastest, no MCP round trips)
```bash
.venv/Scripts/python.exe -c "from pazl.core import chars, roblox; chars.create('hero', preset='roblox', quality='mid'); chars.wear('hero','tshirt',color='#eeeeee'); print(chars.export('hero')['tris']); roblox.export_char('hero')"
```
The running app server keeps old Python code until it is restarted; the web files (`web/`) are read fresh on reload.

## Look at it in the app (the user judges results there)
- App: http://127.0.0.1:8765/ in the built-in browser. Another chat may own the dev servers: just navigate to the running one.
- Show any GLB under `projects/`: `await window.pazl.viewGlb('chars/hero.glb')` in `javascript_tool`. First switch to a non-building tab (`document.querySelector('#segWs button[data-ws="transport"]').click()`), otherwise the open building project reloads over your model.
- Camera: `const {camera, orbit, modelBox, THREE} = window.pazl; const c = modelBox.getCenter(new THREE.Vector3()); orbit.target.copy(c); camera.position.set(c.x + .8, c.y + .4, c.z + 2.6); orbit.update();` Our models face **+Z**; the app's «Перед» button looks from -Z.
- Use `computer screenshot` (with `scale: .6`). Both `zoom` and a screenshot right after a change can return the previous frame: call `invalidate(true)` twice with a pause, or take the screenshot twice.
- Показ menu: «Каркас», «UV-чекер», «Нормали» work for every model.
- Do not add `?r=N` to `viewGlb` paths: it breaks the file URL.

## Compare with the user's original (do this before any change)
```bash
.venv/Scripts/python.exe -I scripts/glb_compare.py projects/refs/<case>/original.glb projects/refs/<case>/mine.glb
```
One table: triangles (total and per mesh), proportions, silhouette per height band, "worse" marks. It reads the bind pose: a skinned file whose default pose differs (our arms-down characters) still measures as T-pose. Copy refs into `projects/refs/<case>/` so the app can open them.

## "1 к 1" with the user's textures
Do not hand-build: rebuild with `pazl/core/retopo.py` (shrinkwrap + cards, xatlas UVs, bake of the original textures). Worked example and steps: `scripts/rebuild_roblox_avatar.py`, docs/ROBLOX.md "1:1 rebuild". Compare `posed_all.glb` next to the original in the app (load both with GLTFLoader into `pazl.root`).

## Budgets (from the user's originals)
| Model | Original | Ours now |
|---|---|---|
| Roblox avatar (body + hair/hat + pet) | 5,078 tris (body 2,436, hair+hat 1,520, pet 1,122) | 4,440 (`galaxy_1to1`, 1:1 rebuild with original textures); 4,436 (`galaxy_woof`, generator) |
| Game building | 3.7-4k tris, windows are texture | see docs/photo_to_model.md |
| Vehicle | Kenney/KayKit 300-1,500 | docs/model_craft.md |

## Rules from the user
- Focus on the 3D model, animations and movement. Do **not** draw pictures/textures yourself; take textures from CC0 sources (`skin_search`, `skin_download`) or the user's files.
- Always show the result in the app with a screenshot.
- Commit at the end with a version bump (see the latest `git log`).
- Spend few tokens: measure with scripts, not with many screenshots; read only the files in the table above.
