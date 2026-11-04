# Characters, clothes, web textures and Roblox export: guide for every AI

Works the same from MCP (`pazl`), from the app's chat and over HTTP (`http://127.0.0.1:8765/api/ws/...`).

## Dress a character
1. `char_import(path, height=1.6)` for a file on disk, or `char_make(name, preset="blocky")`. Use `quality="mid"` or `"low"` for Roblox.
2. `char_wear(name, kind, color=..., skin=...)`. Kinds: tshirt longsleeve tank jacket pants shorts skirt dress cloak boots shoes gloves scarf belt beanie hat hair_short hair_long beard.
3. Look at the result in the app: tabs Персонажи, Одежда.

## 1:1 rebuild of a reference model with its own textures (the way to do "сделай 1 к 1")
`scripts/rebuild_roblox_avatar.py [ref.glb] [name]` (~45 s) -> character `galaxy_1to1`, 3,573 tris vs 5,078 (body 1,464), same look and pose:
1. Reference moved into our frame (studs x 0.28 = metres, turned to face +Z).
2. Body cut into head/torso/arms/legs by whole reference pieces; each block = our grid box shrinkwrapped onto it (exact closest point on the reference triangles), head = shrinkwrapped icosphere. Hair, hat, pet piece by piece: strands -> 4-triangle cards, bigger pieces shrinkwrapped (`pazl/core/retopo.py`).
3. Own UV atlas (xatlas), then the ORIGINAL textures baked onto it (closest reference point facing the same way). No hand-made pictures.
4. Arms raised about their joint for a T-pose bind; the measured arm angle is stored as `rest_pose`, so the file shows the reference pose and clips still work. Block -> bone map in `body_t.labels.npz` (`labels` in the recipe).
5. Hair+hat and pet are `acc_head` / `acc_chest` (textured GLB that follows a bone), so nothing clips: they keep the reference placement.
Outputs in `projects/refs/<case>/rebuild/`: `posed_all.glb` (compare with the original in the app), `body_t.glb`, `hair_hat.glb`, `pet.glb`.
v0.63 (after "всё кривое и косое"): the body is no longer shrinkwrapped piece by piece. It is 15 clean R15 parts (head, upper/lower torso, upper arm, lower arm, hand, upper leg, lower leg, foot), each a `retopo.loft` of 3-7 rings measured on the reference along the part's own axis (arms follow their 12 deg tilt, so every block is straight and aligned). Joints come from the reference's flat joint discs. UV: own layout, `retopo.pack` - one side strip per part (seam at the back, front reads left to right, top up) plus caps, same texel density everywhere, nothing mirrored; it is a layout you can paint on in other programs. Every part follows its own bone (elbows and knees bend without gaps). Hair strands are flat ribbons growing from the scalp (`retopo.ribbon`). The UV checker in the app now uses the glTF convention (it showed every label mirrored before).
Fixes after the user's wireframe check (v0.61.2): the body is rebuilt piece by piece like R15 (head, upper torso, lower torso = `hips`, arms, legs; the hip piece spanning both legs stays whole); an open side of a piece (shirt hem) gets a flat cap instead of a funnel (`shrinkwrap(box=...)`); flat pieces (hair locks, hat fold, joint discs) become one-layer sheets (`retopo.sheet`), never slabs. The original is exported unlit (`KHR_materials_unlit`), so it always looks brighter than a lit model.
Mistakes found on the way: glTF metallic defaults to 1 (set `metallicFactor=0` or the model renders dark); snapping to surface samples makes flat faces ripple (project onto the triangles); a mirrored oriented box turns a primitive inside out (check the determinant); cutting by triangle centres puts shoulder caps into the torso (cut by whole pieces).

## Lessons from a real Roblox avatar (user's original, 2026-11-04, `projects/refs/roblox_galaxy/`)
- Real avatar: 5,078 triangles. Body = ONE mesh of 2,436 tris; shirt, pants, face are all texture on it. Hair + beanie 1,520, pet 1,122.
- My first try had 45,451 (x9): every garment was a second 3D shell. Now on block bodies `tshirt longsleeve tank jacket pants shorts boots shoes gloves` are **painted onto the body faces** (`cloth.PAINT`); hair/hats stay 3D but are capped at 1,200 tris. Set `cloth3d: true` in the recipe to get the old shells.
- Block bodies are built straight from boxes on a grid (`body.blocky_mesh`), head rounded like a Roblox head: ~1.8k tris at `mid`, clean clothing lines (sampled at grid-quad centres).
- Preset `roblox` has R15 proportions: legs 0.47 of the height (to the top of the head), torso 0.33, head 0.23, torso width 0.4.
- Roblox avatars face **-Z**, ours +Z: `roblox_export` now turns `model.glb` and accessories half round.
- Arms down: the bind stays T-pose (rigging, clay, clips need it), but the GLB's default node pose has the arms lowered (`rest: "down"`, the default; `"t"` for a T-pose file), so viewers and Studio show the figure like a game avatar and every clip still plays.
- Game hair and hats from primitives (`chars.PROPS`, follow the head bone): `hair_spiky` = scalp cap + ~100 flat strands swept to one side (~800 tris, `side`, `seed`), `beanie_back` = slouchy beanie on the back of the head (~340 tris, `tilt`), `bird` sits on the chest edge beside the head.
- `galaxy_woof` now: 4,436 tris (original 5,078). Its face is a texture in the original and is not made here (textures come from the user).

Extras: `print="skins/prints/<file>.png"` (+ `print_size`, share of chest width) on a top puts a picture on the chest, also on the Roblox shirt front; kind `bird` is a pet on the right shoulder (`side="L"` for the left), exported as `accessories/bird.glb`; skin preset `galaxy` is a space pattern. Example: character `galaxy_woof` (blocky, longsleeve+pants `galaxy`, white `tank` with a chest print, grey shoes, galaxy hair, beanie, bird).

Viewport checks (menu Показ, every workshop): «Каркас» white wire overlay, «UV-чекер» swaps materials for a numbered grid (magenta = no UVs), «Нормали» draws vertex normals, they follow the animation.

A file with several figures (separate meshes standing apart) becomes `<name>_1`, `<name>_2`, ... Block bodies (R6 style) are dressed block by block, so cloth does not tear when they walk.

## Textures from the internet
1. `skin_search("leather")` searches Poly Haven and ambientCG. Both are CC0: free, commercial use allowed, no attribution required.
2. `skin_download(source, id)` saves the texture as a skin in `projects/skins/`, with its source and license in `<id>.skin.json`.
3. Use the returned name anywhere: `char_wear(..., skin=name)`, `skin_apply(src, name)`, `char_make(name, skin=name)`.

Do not download from sites without a clear license. Links: https://polyhaven.com/license, https://docs.ambientcg.com/license/, API https://api.polyhaven.com/assets, https://ambientcg.com/api/v2/full_json

## Export for Roblox
- `roblox_export(char="name")` writes `projects/roblox/<name>/`: `shirt.png`, `pants.png`, `model.glb`, `anim_*.rbxmx`, `accessories/*.glb`, `README.txt`.
- `roblox_export(path="items/mug.glb")` or a PNG under `projects/`: a ready copy of any model, sprite sheet or picture.
- In the app: button «⬇ Для Roblox» in every workshop.

| What | File | Where it goes | Docs |
|---|---|---|---|
| Shirt, pants | 585x559 PNG on the official template | Creator Dashboard > Avatar Items > Classics. 80 Robux per upload, Studio test is free | https://create.roblox.com/docs/avatar/classic-clothing |
| Model, rig | GLB | Studio > File > Import 3D | https://create.roblox.com/docs/art/modeling/3d-importer |
| Limits | | see the specifications page | https://create.roblox.com/docs/art/modeling/specifications |
| R6 animation | KeyframeSequence `.rbxmx` | Studio > Insert from File, then Animation Editor | https://create.roblox.com/docs/animation/editor |
| Accessory | GLB, up to 4000 triangles | Import 3D, then Accessory Fitting Tool | https://create.roblox.com/docs/art/accessories |
| Picture, sprite sheet | PNG up to 1024 px | Asset Manager or Decals | https://create.roblox.com/docs/projects/assets |

Template regions (x, y, w, h), measured from Roblox's `Classic-Clothing-Templates.zip`: torso top 231,8,128,64; front 231,74,128,128; bottom 231,204,128,64; sides 165,74,64,128 and 361,74,64,128; back 427,74,128,128. Limb tops 217,289 and 308,289 (64x64); limb bottoms 217,485 and 308,485; limb sides 64x128 at y=355, x=19,85,151,217 and 308,374,440,506.

Not produced: layered clothing (it needs inner and outer cages). Classic clothing is flat paint on the body, so skirts, cloaks and hair have no 3D shape there. Published items must pass Roblox moderation and must not use others' brands.
