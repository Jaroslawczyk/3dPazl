# Characters, clothes, web textures and Roblox export: guide for every AI

Works the same from MCP (`pazl`), from the app's chat and over HTTP (`http://127.0.0.1:8765/api/ws/...`).

## Dress a character
1. `char_import(path, height=1.6)` for a file on disk, or `char_make(name, preset="blocky")`. Use `quality="mid"` or `"low"` for Roblox.
2. `char_wear(name, kind, color=..., skin=...)`. Kinds: tshirt longsleeve tank jacket pants shorts skirt dress cloak boots shoes gloves scarf belt beanie hat hair_short hair_long beard.
3. Look at the result in the app: tabs Персонажи, Одежда.

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
