"""Inspect a reference GLB without trimesh (numpy only): world-space bbox per mesh, materials, texture dump.

    python scripts/glb_inspect.py ref.glb [--tex DIR] [--min-size 0.5]

Prints overall world bbox (Y up), tris, and one line per mesh: name, material ids, world min, size [x,y,z].
--tex DIR saves embedded images (img<N>.png/jpg) + a contact sheet DIR/sheet.jpg to see which atlas is what.
Tips: small repeated parts (fans, ladders) = same size lines; --min-size hides tiny ones.
"""
import argparse, json, struct
from pathlib import Path
import numpy as np


def load(path):
    f = Path(path).read_bytes()
    n = struct.unpack("<I", f[12:16])[0]
    return json.loads(f[20:20 + n]), f[28 + n:]


def mat(n):
    if "matrix" in n:
        return np.array(n["matrix"]).reshape(4, 4).T
    m = np.eye(4)
    if "scale" in n:
        m = np.diag(list(n["scale"]) + [1]) @ m
    if "rotation" in n:
        x, y, z, w = n["rotation"]
        r = np.eye(4)
        r[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
        m = r @ m
    if "translation" in n:
        t = np.eye(4)
        t[:3, 3] = n["translation"]
        m = t @ m
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb"); ap.add_argument("--tex"); ap.add_argument("--min-size", type=float, default=0.0)
    a = ap.parse_args()
    j, blob = load(a.glb)
    rows, tris = [], 0

    def walk(i, P):
        nonlocal tris
        n = j["nodes"][i]; W = P @ mat(n)
        if "mesh" in n:
            mesh = j["meshes"][n["mesh"]]; lo = np.full(3, 1e9); hi = -lo; t = 0
            for p in mesh["primitives"]:
                ac = j["accessors"][p["attributes"]["POSITION"]]
                for c in range(8):
                    v = np.array([ac["max"][k] if c >> k & 1 else ac["min"][k] for k in range(3)] + [1])
                    w = (W @ v)[:3]; lo = np.minimum(lo, w); hi = np.maximum(hi, w)
                if "indices" in p: t += j["accessors"][p["indices"]]["count"] // 3
            tris += t; rows.append((n.get("name"), [p.get("material") for p in mesh["primitives"]], lo, hi - lo, t))
        for c in n.get("children", []): walk(c, W)

    for s in j["scenes"][0]["nodes"]: walk(s, np.eye(4))
    lo = np.min([r[2] for r in rows], 0); hi = np.max([r[2] + r[3] for r in rows], 0)
    print(f"meshes {len(rows)} tris {tris} bbox min {lo.round(2)} size {(hi-lo).round(2)} (X,Y-up,Z; front usually +Z)")
    for nm, m, mn, sz, t in rows:
        if sz.max() >= a.min_size: print(f"{nm:18} mat{m} tris{t:6} min{mn.round(2)} size{sz.round(2)}")
    for i, m in enumerate(j.get("materials", [])):
        pb = m.get("pbrMetallicRoughness", {}); tx = pb.get("baseColorTexture", {}).get("index")
        src = j["textures"][tx]["source"] if tx is not None else None
        print(f"mat{i} {m.get('name')} tex_src={src} colour={pb.get('baseColorFactor')}")
    if a.tex:
        from PIL import Image
        d = Path(a.tex); d.mkdir(parents=True, exist_ok=True); ims = []
        for i, im in enumerate(j.get("images", [])):
            bv = j["bufferViews"][im["bufferView"]]; o = bv.get("byteOffset", 0); data = blob[o:o + bv["byteLength"]]
            p = d / f"img{i}.{'png' if data[:4] == b'\x89PNG' else 'jpg'}"; p.write_bytes(data); ims.append(p)
        W = Image.new("RGB", (5 * 300, ((len(ims) + 4) // 5) * 300))
        for i, p in enumerate(ims):
            t = Image.open(p).convert("RGB"); t.thumbnail((300, 300)); W.paste(t, (i % 5 * 300, i // 5 * 300))
        W.save(d / "sheet.jpg"); print("saved", len(ims), "images + sheet.jpg in", d)


main()
