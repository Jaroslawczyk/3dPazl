# 3dPazl — guide for AI agents

Parametric building constructor. You describe a building as a **recipe** (JSON list of elements); the app
generates watertight geometry, welds everything into one closed mesh, validates it and renders checks.
Units: meters. Z is up. Facades: X along the wall, Y outward.

## Workflow (cheap in tokens)
1. `list_styles` → pick a style (sets materials + default proportions). `list_elements` once if needed.
2. `new_building(name, style, elements=[...])`. Fastest start: one macro, e.g. `{"id":"b","type":"orthodox_church"}`.
3. `validate` → fix every error (floating parts are listed with element ids and coordinates).
4. `render_views` → ONE image, 16 views (4 sides, 4 isometric, 3 eye-level, top, below, section, plans of the 1st floor and mid height — check floors, walls and textures inside the cuts too). Red = problem elements.
   Check every view, not just the front. Zoom: `render_views(views=["iso_fl","front"], tile_w=640)` or `render_custom`.
5. `patch` small changes, repeat 3–4. Then `export` (glb) and `texture_manifest`.
6. Use `note("...")` to tell the user what you are doing — they watch the live log and the 3D view.

## Recipe element
```json
{"id": "main", "type": "block", "params": {"w": 12, "d": 9, "floors": 3},
 "on": "hostId:anchor", "at": [u, v], "offset": [x, y, z], "rot": 0,
 "repeat": {"count": 4, "step": [5, 0, 0]}, "mirror_u": false,
 "subtract": false, "cut": ["otherId"], "material": "brick_red", "hidden": false}
```
- `on` attaches to an anchor of another element. Never place by guessing absolute coordinates when an anchor exists:
  attached parts can't float.
- Face anchors (`block:front|right|back|left|face0..N`, `tower:face0..N`, `dormer:front`): `at=[u, v]`,
  u = meters from the left edge of the face (seen from outside), v = height. `"50%"` works. Single items
  (door, window, panel, canopy, stairs) default to u = centre; grid items (windows, balconies, buttresses,
  pilasters, timber_frame, panel_grid, curtain_wall, colonnade) lay themselves out over the whole face.
- Top anchors (`block:top`, `block:floor2`, `tower:top`, `roof:top`): `at=[x, y]` from the footprint centre.
- Point anchors: `roof:ridge`, `dome:top`, `spire:top`, `origin` (any element).
- Square towers: face0=north(+Y), face1=west(-X), face2=south(-Y), face3=east(+X). Round towers: 8 tangent faces,
  face7 = east, face0 = north-east … (counter-clockwise).
- Block `front` faces -Y, `right` +X, `back` +Y, `left` -X.
- `anchors(id)` lists anchors with sizes, floors, floor height of a built element.

## Elements (see `describe_element(type)` for params)
- structure: block (hollow building volume, floors, plinth), wall, tower, log_cabin (сруб), platform (stylobate),
  stairs, mound (earth), step_pyramid (smooth/stepped/ziggurat), pylon, minaret, stupa, iwan; primitives: box, cylinder, sphere, prism, revolve, hull, beam — combine for anything unusual.
- openings: windows (grid), window, door/portal (orders, steps, canopy), niche, bay_window (эркер). Shapes: rect, arch, segmental, lancet,
  round, rose, horseshoe, ogee, slit, ribbon, triangle. Trims: simple, classic, pediment, segment_pediment, baroque,
  gothic_hood, nalichnik, archivolt, rustic, soviet.
- roofs: roof (gable, hip, half_hip, pyramid, tent, shed, mansard, gambrel, flat, cone, dome, onion, helmet, bell,
  barrel, cross_gable, pagoda, chinese (curved, upturned corners), irimoya, sawtooth), dome (half=true for semi-domes) (drum, windows, kokoshniki, lantern, cross), spire, cross, chimney, dormer, pinnacle, shikhara (Hindu tower).
- columns: column (doric, tuscan, ionic, corinthian, composite, egyptian, plain, square, byzantine, wood_post),
  colonnade/portico, pilasters.
- decor: cornice (crown, dentil, corbel, lombard, machicolation, band, soviet), battlements, buttresses (+flying),
  quoins, timber_frame (фахверк), panel_grid (швы панелей), balconies/loggias, canopy, curtain_wall, balustrade,
  fence, pediment, gable_wall (Dutch stepped/neck/bell gables), chhatri, obelisk, panel (mosaic, fresco, painting, icon, relief, sign, clock — unique texture slot from `subject`).
- macros (whole buildings → editable children): house, izba, dugout, fachwerk_house, panel_building (1-464, 1-447,
  121, P-44, II-18), gothic_cathedral, orthodox_church, greek_temple, castle_keep, glass_tower, lithuanian_church,
  palazzo, stalinka, romanesque_church, baroque_church, constructivist, roman_pantheon, egyptian_temple, giza_pyramid,
  ziggurat, maya_pyramid, byzantine_church, caucasian_church, ottoman_mosque, persian_mosque, moorish_palace,
  mughal_mausoleum, hindu_temple, chinese_temple, pagoda, japanese_house, stave_church, dutch_house, victorian_house,
  alpine_chalet, art_deco_tower, brutalist_block, factory, bunker.

## Random sizes, mixes, styles
- Any numeric param can be random: `{"rand":[3,7]}` (one value), `{"mix":[5,9]}` (a different value for every
  copy/section/house — panel_building sections, dutch_house rows, `repeat` copies), `{"choice":[...]}`.
  Stable per recipe `seed`; `set_options(reroll=true)` re-rolls.
- Style mix: recipe or element `"style": "gothic+russian_orthodox"` — the first style rules materials/proportions,
  the second fills the rest. Any element (and its macro children) can carry its own `style`.
- Styles have `years`, `regions`, `palette` (see `list_styles`) — the library filters by epoch and territory.

## Facades, paint, decals, interiors
- `set_facade(id, face, windows)` — swap window style on one side or remove windows (`"none"`).
- `paint(id, colors)` / `paint(random=true)` — element `colors` {role: "#hex"} inherited by macro children.
  Low-poly shows flat colours; realistic tints PBR textures.
- `decal` element on a face (graffiti, dirt, soot, moss, rust, water_stain, crack, peeling, poster, scuff) and
  `weathering` on `<block>:top` (or `weather()` for everything). Decals and the fake room pictures behind windows
  are an OVERLAY layer: separate quads, each at its own depth (no z-fighting), never welded into the watertight shell.
  Toggle with `set_options(interiors=..., decals=...)`.
- `generate_interior()` — rooms/corridors/doors/stairs/elevators/furniture inside every block (`<block>:inner`),
  era-aware (spiral stairs before 1500, elevators from 1880 for tall buildings). Own plans via `plan`.
  Check with `floorplan()` and the `plan` view (horizontal cut) of `render_views`.
- Textures: realistic mode uses PBR maps from `textures/library` (`download_textures()` fetches CC0 packs from ambientCG).

## Shapes and window patterns
- `block` footprints are not only boxes: `shape` = rect, round, oval, rounded, L, U, T, octagon, hexagon, trapezoid,
  wedge (flatiron), bow (curved front), cut_corner, cross; `shape_k` = size of the notch / radius / taper (0.1-0.8),
  `flip: true` mirrors it (asymmetric). Faces `front/right/back/left` exist on every shape (the longest edge facing
  that way); round/oval walls get tangent faces `face0..N`. Use cone/dome roofs on round/oval; gable/hip roofs are
  trimmed to the footprint automatically. Bulk: patch `{"op":"shapes","shape":"random"|"round"|...}`.
- `windows` grids: `fill` = all | random (`fill_share`) | checker | alternate | symmetric | formula (`fill_formula`,
  an expression of c, r, cols, rows, n, e.g. `"(c + r) % 2 == 0"`); the other slots get `fill_other` = mix | blind
  (bricked up) | shutters | boarded | none. Bulk: `{"op":"windows_fill","fill":"random"}`.
- A window grid never puts a window where a door / single window / bay already is on the same face.

## Game styles, export
- Game looks (region `games`): `blocky_toy` (Roblox-like toy bricks; `game_house` macro + `studs` on flat roofs),
  `voxel`, `fantasy_rpg`, `cyberpunk`, `post_apocalyptic`, `cartoon`, `scifi`. Each has sub-styles with id
  `<style>_<variant>`, e.g. `blocky_toy_classic`, `blocky_toy_neon`, `voxel_desert`, `fantasy_rpg_elven`,
  `cyberpunk_slums`, `scifi_station` (`list_styles` shows them with `parent`).
- `export(format, only=[ids])`: glb, gltf (self-contained), obj (+mtl+textures), dae, 3mf, stl, ply, off.
  `only` exports just those elements with their children and everything attached. Y-up for glb/gltf/obj/dae
  (game engines, Roblox Studio: obj or gltf), Z-up for 3mf/stl/ply/off.

## Doors, brick builder, destruction (set_options)
- Door leaves are separate objects on hinges (`doors_separate`, default true): in exports each leaf is a node with
  its pivot on the hinge; `<name>.objects.json` lists hinge, axis and open angle (negative = inward) for game animation.
  The opening keeps a static door frame. `doors_separate: false` welds them like before.
- `build_mode: "bricks"` builds everything from cubic bricks of `brick_size` m (voxel / toy-brick games): bricks fill
  the solid volume (openings wider than a brick stay open, glazed windows become glass bricks), every brick face
  takes the colour of the surface facing that way. `brick_cull: true` keeps only visible faces (watertight);
  false = every brick a full cube. Renders and validate still use the solid model.
- `fracture: {"on": true, "level": "light|medium|heavy|extreme" (12/40/100/250 pieces) | "pieces": N,
  "mode": "voronoi|elements"}`: exports become one object per chunk (pivot = centre of mass, break faces `rubble`,
  volumes in `.objects.json`); with bricks, chunks are groups of bricks, level "bricks" = every brick a piece.

## Checks
`validate` reports floating parts, open edges, z-fighting spots (two surfaces < 2 mm apart), overlapping decals,
degenerate triangles. `render_views` default = 16 views: 4 sides, 4 isometric, 3 eye-level from the ground, top,
below, section, plan (1st floor) and plan_mid (mid height). Look at the floors and walls inside the cuts: a floor split into random triangles of two materials means two solids share that plane.

## Editing macro children
Children ids look like `b/roof`. `patch([{op:"update", id:"b/roof", params:{pitch:50}}])` stores an override in the
macro. `{op:"remove", id:"b/chimney"}` hides a child. `{op:"explode", id:"b"}` turns the macro into plain elements.

## Building a real building from photos
1. Estimate overall size from known references (floor ≈ 3 m, door ≈ 2.1 m, window ≈ 1.5 m, step ≈ 0.16 m).
2. Massing first: blocks/towers for each volume, overlapping where they join (union welds them).
3. Roofs on `:top` anchors. Then openings per face, then decor. Validate + render after each stage.
4. Match the style: set `style`, then override materials per element (`material`) where the photo differs.

## Rules for clean models
- Everything must touch something: attach via anchors, overlap volumes by ≥5 cm. Validation lists floating parts.
- Walls stay closed: windows/doors cut real holes and add frames + glass; roofs fill gables; top slabs close blocks.
- Low-poly: `{op:"set", key:"detail", value:"lowpoly"}` — fewer segments, no micro-decor, flat shading.
- Exports are welded into one watertight mesh with materials (+ box-projected UVs). `lod_tris` decimates for LODs.

## HTTP API (for agents without MCP)
Base `http://127.0.0.1:8765/api`, header `X-Agent: <your name>`.
GET state, recipe, tree, anchors/{id}, element/{id}, catalog/styles, catalog/elements, catalog/element/{type},
projects, log?since=; POST new, load, save, patch {ops,note}, undo, redo, validate, render {views,tile,custom},
export {format,lod_tris,force}, textures/manifest, note {text}, camera {az,el,dist,target}.
GET preview.glb (per element), model.glb (welded, textured), render/latest.png.
