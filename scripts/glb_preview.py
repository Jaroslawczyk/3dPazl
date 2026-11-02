"""Headless preview of a GLB (numpy+PIL, no GPU): vertex splatting with texture colour sampled at each UV, z-buffered.

    python scripts/glb_preview.py model.glb out.png [--views az:el,...] [--size 500]
Area-weighted point sampling (500k points/primitive) = solid-looking preview for scans and low-poly alike.
Pass views with = because of the minus sign: --views="-35:25,145:25".
"""
import argparse, io, json, struct
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument("glb"); ap.add_argument("out")
ap.add_argument("--views", default="-35:25,35:25,145:25,0:89"); ap.add_argument("--size", type=int, default=500)
a = ap.parse_args()
f = open(a.glb, "rb").read(); n = struct.unpack("<I", f[12:16])[0]; j = json.loads(f[20:20 + n]); blob = f[28 + n:]
CT = {5126: "<f4", 5123: "<u2", 5125: "<u4"}; NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def acc(i):
    A = j["accessors"][i]; bv = j["bufferViews"][A["bufferView"]]; c = NC[A["type"]]; dt = np.dtype(CT[A["componentType"]])
    o = bv.get("byteOffset", 0) + A.get("byteOffset", 0); st = bv.get("byteStride") or c * dt.itemsize
    arr = np.ndarray((A["count"], c), dt, blob, o, (st, dt.itemsize)); return arr.astype(float)


def img(i):
    bv = j["bufferViews"][j["images"][i]["bufferView"]]; o = bv.get("byteOffset", 0)
    return np.asarray(Image.open(io.BytesIO(blob[o:o + bv["byteLength"]])).convert("RGB").resize((1024, 1024)))


def mat(nd):
    if "matrix" in nd: return np.array(nd["matrix"]).reshape(4, 4).T
    m = np.eye(4)
    if "scale" in nd: m = np.diag(list(nd["scale"]) + [1]) @ m
    if "rotation" in nd:
        x, y, z, w = nd["rotation"]; r = np.eye(4)
        r[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
        m = r @ m
    if "translation" in nd: t = np.eye(4); t[:3, 3] = nd["translation"]; m = t @ m
    return m


pts, cols = [], []
def walk(i, P):
    nd = j["nodes"][i]; W = P @ mat(nd)
    if "mesh" in nd:
        for p in j["meshes"][nd["mesh"]]["primitives"]:
            v = acc(p["attributes"]["POSITION"]); v = (np.c_[v, np.ones(len(v))] @ W.T)[:, :3]
            m = j["materials"][p.get("material", 0)]; pb = m.get("pbrMetallicRoughness", {})
            uv = acc(p["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in p["attributes"] else None
            if "indices" in p:                      # sample K random points inside every triangle (dense surface)
                ix = acc(p["indices"]).astype(int).reshape(-1, 3)
                ar = np.linalg.norm(np.cross(v[ix[:, 1]] - v[ix[:, 0]], v[ix[:, 2]] - v[ix[:, 0]]), axis=1) + 1e-12
                rng = np.random.default_rng(1)
                pick = rng.choice(len(ix), size=500000, p=ar / ar.sum())          # area-weighted -> uniform density
                r1, r2 = rng.random((2, len(pick))); f = r1 + r2 > 1; r1[f], r2[f] = 1 - r1[f], 1 - r2[f]
                t = ix[pick]; w0, w1, w2 = (1 - r1 - r2)[:, None], r1[:, None], r2[:, None]
                nv = v[t[:, 0]] * w0 + v[t[:, 1]] * w1 + v[t[:, 2]] * w2
                nuv = None if uv is None else uv[t[:, 0]] * w0 + uv[t[:, 1]] * w1 + uv[t[:, 2]] * w2
                v, uv = np.vstack([v, nv]), (None if uv is None else np.vstack([uv, nuv]))
            if uv is not None and "baseColorTexture" in pb:
                t = img(j["textures"][pb["baseColorTexture"]["index"]]["source"])
                c = t[(np.clip(uv[:, 1] % 1, 0, .999) * 1024).astype(int), (np.clip(uv[:, 0] % 1, 0, .999) * 1024).astype(int)]
            else:
                c = np.tile(np.array(pb.get("baseColorFactor", [.7, .7, .7])[:3]) * 255, (len(v), 1))
            pts.append(v); cols.append(c)
    for c in nd.get("children", []): walk(c, W)
for s in j["scenes"][0]["nodes"]: walk(s, np.eye(4))
P = np.vstack(pts); C = np.vstack(cols); ctr = (P.min(0) + P.max(0)) / 2; ext = (P.max(0) - P.min(0)).max()
S = a.size; views = [tuple(map(float, v.split(":"))) for v in a.views.split(",")]
out = Image.new("RGB", (S * len(views), S), (110, 110, 120))
for k, (az, el) in enumerate(views):
    az, el = np.radians(az), np.radians(el); q = (P - ctr) / ext
    R1 = np.array([[np.cos(az), 0, -np.sin(az)], [0, 1, 0], [np.sin(az), 0, np.cos(az)]])
    R2 = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    r = q @ R1.T @ R2.T; x = ((r[:, 0] * .85 + .5) * (S - 1)).astype(int); y = ((.5 - r[:, 1] * .85) * (S - 1)).astype(int)
    d = r[:, 2]; o = np.argsort(d)   # far first, near overwrites
    buf = np.full((S, S, 3), (110, 110, 120), np.uint8); ok = (x >= 0) & (x < S) & (y >= 0) & (y < S); o = o[ok[o]]
    for dx in (0, 1, 2):
        for dy in (0, 1, 2):
            buf[np.clip(y[o] + dy, 0, S - 1), np.clip(x[o] + dx, 0, S - 1)] = C[o].astype(np.uint8)
    out.paste(Image.fromarray(buf), (k * S, 0))
out.save(a.out); print("saved", a.out)
