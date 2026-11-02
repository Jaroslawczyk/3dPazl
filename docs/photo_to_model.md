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
