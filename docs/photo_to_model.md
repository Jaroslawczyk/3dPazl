# Photo -> model -> GLB compare playbook (learned on 2 cases)

1. **Photos**: identify volumes (tall/low block), roof gear, mast; get proportions as RATIOS of photo pixels
   (length : depth : height). Do not guess metres - one known size (floor ~3 m, door 2.1 m) fixes the scale.
2. **Build** in pazl (recipe in one `new_building` call): blocks, `windows`, `door`, parapet boxes, `beam`/`cylinder`
   decor; attach everything with `on` anchors; `validate` -> floating parts -> fix; ONE `render_views` of 3-4 views.
   Cylinders/beams with `offset` above the host float: start them on the host.
3. **Reference GLB arrives**: `python scripts/glb_inspect.py ref.glb --min-size 5 --tex ref_x` (numpy only, no trimesh):
   world bbox (Y up, front +Z, building centre x), per-mesh sizes, materials, atlas sheet. Compare ratios with my model
   and fix proportions FIRST, then decor positions (mesh min/size = exact positions).
4. **Textured copy**: `scripts/textured_radio_station.py` is the template (trimesh via `.venv/Scripts/python.exe`):
   Builder boxes + PIL facade textures + tube()/cylinders for pipes, ladders, fans; wall colour cut from the reference
   atlas (textures/library/<ref>/building_atlas_albedo.png). Preview with model-viewer html in projects/<p>/export,
   `http://127.0.0.1:8765/files/<p>/export/view.html` (wait ~10 s for the CDN; add ?r=N to bust cache).
5. **Save for reuse**: textures -> textures/library/<ref>/ (+README with source/licence), decor -> `library_save`
   (spire, dish, roof fan, ladder rail), generator script -> scripts/.
6. Pitfalls: pazl cannot apply atlas UVs; AO/platform PNGs contain black (do not use as top texture); copying the
   original GLB is not "building" - say so; atlas tiles repeat as stripes unless blended to the mean colour.

## Case 3 notes (office tower)
- `glb_inspect.py` on a 30 MB ref: only 4k tris, 16 images = tileable PBR facades (windows tile 2 bays x 3 floors).
  Saved to textures/library/ref_office_tower/. Template: scripts/textured_office_tower.py (438 tris vs 88k in pazl recipe).
- Facade = PIL tile of the reference tile repeated per face; logo/text drawn undistorted then resized to the face's
  px-per-unit; dark text on dark glass needs a light stroke. Brightness 0.6 on tile makes glass read dark.
- Choose pazl recipe only for geometry you can't paint; for glass towers texture scripts are 200x cheaper.

## Verification checklist (do BEFORE saying done)
1. `python scripts/glb_inspect.py mine.glb | head -1` vs the same for the ref: bbox size must match (tower x4 scale,
   radio 33 x 35.96 x 22.62). Fix > 2 % differences (found: spire 0.6 too tall, ground disc centre off by 1 unit).
2. Compare per-mesh min/size of the big parts (core, piers frame, disc) with the ref lines.
3. Screenshot in the viewer (wait 10 s twice); check logo/text readable, no black/transparent faces, nothing floating.
4. Regenerate from scratch (delete old glb) so no stale file is judged.

## Case 4 notes (jungle stilt house, AI/Tripo scan 132k tris, one baked 4k atlas)
- No photos given: `scripts/glb_preview.py ref.glb out.png` (headless vertex-splat render) showed the shape; browser viewer was
  denied on the first navigate - fall back to that. Baked atlas is NOT tileable: keep only as colour reference
  (textures/library/ref_jungle_house/).
- Built in pazl (1.1k tris): 8 posts + floor slab, rear enclosed block, gable roof on a thin helper block (`rb`) sized to the
  whole footprint, porch posts/rails, ladder beams, rock sphere. Ref ratios W:L:H = .77:1:.67 -> mine .84:1:.59 (check again).
- Pitfall: a sphere centred at z=0 is half underground; offset z by its radius. `info separate_grounded_parts` for a rock is fine.

### Case 4 redo (user: "very unlike")
- Cause: I judged the scan from a sparse vertex preview and built a pazl block hut. Reference was a stilt house with long
  front roof over a plank deck, weathered grey planks, patchwork rusty roof, slender posts, side ladder, hanging cloth.
- Fix: glb_preview.py now samples 500k area-weighted points (solid look) - ALWAYS view the ref in this before building.
  Rebuilt as scripts/textured_jungle_house.py (400 tris, procedural plank/roof textures). Ladder inflated the bbox: check W:L:H.
- Rule: "looks unlike" => first re-look at the ref at 3 angles at 600 px, list 6 defining features, tick them off in my render.

## Case 5 notes (medieval stone cottage, 28k tris, 5 baked atlases)
- Preview the ref first (3 angles, 600 px): stone walls + timber posts, half-timbered gables, steep brown thatch, arched plank door
  on the gable end. Atlases are baked but contain usable flat panels: crop tiles (tile_stone/tile_roof/tile_door) into
  textures/library/ref_medieval_house/ and tile them with alternate flips (hides seams).
- scripts/textured_medieval_house.py (238 tris). Door must fit under the wall top (arch height + radius < wall height).

## Case 6 notes (low-poly fishing house, flat colours, 13.7k tris, NO textures)
- glb_inspect showed 29 named parts with baseColorFactor only => ideal for a pazl recipe (boxes/cylinders/beams, `paint` per element)
  and it opens natively in the app (unlike script GLBs). Units are cm: divide by 100; world coords are raw (not centred).
- glTF colour factors are LINEAR: convert with 255*f**(1/2.2) before painting (preview tools show them raw = too orange).
- Built `fishing_house` (878 tris, bbox 10.45 x 9.87 x 20.79 vs ref 10.45 x 10.0 x 20.8). Floating checks: barrel must touch its
  pillar top, ladder must touch a wall.
- Case 6 redo ("closer, all angles"): v1 was a MIRROR image (I used my_y = +ref_z). Correct Y-up -> Z-up mapping that keeps
  handedness: (x, y, z)_ref -> (x, -z, y)_mine. Then place EVERY part from its measured world bbox (glb_inspect min/size), check
  4 sides (az 0/90/180/270) against the ref, not just 3/4 views. Elements can be generated from a python list and sent via
  POST /api/new (server on :8765) instead of pasting JSON. Per-element colour: recipe element `"colors":{"wall":"#hex"}` works.
