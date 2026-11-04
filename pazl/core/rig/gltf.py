"""Minimal glTF 2.0 binary writer for one skinned mesh with a joint hierarchy and animations (own code)."""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

from . import anim
from .skeleton import order

FLOAT, U16, U32 = 5126, 5123, 5125


def write(path, V, F, N, C, joints, weights, bones, clips: dict):
    return write_parts(path, [{"name": "Body", "V": V, "F": F, "N": N, "C": C, "J": joints, "W": weights}], bones, clips)


def write_parts(path, parts, bones, clips: dict):
    """Several skinned meshes on one skeleton. Part: {name, V, F, N, J, W, C? (vertex colours), UV? + png? (texture),
    metal?, rough?}; used by clothes: each garment keeps its own material."""
    names, par, heads, _ = order(bones)
    buf = bytearray()
    views, accs = [], []

    def add(arr, comp, typ, target=None, minmax=False):
        arr = np.ascontiguousarray(arr)
        while len(buf) % 4:
            buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": arr.nbytes, **({"target": target} if target else {})})
        buf.extend(arr.tobytes())
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": len(arr), "type": typ}
        if minmax:
            a2 = arr.reshape(len(arr), -1)
            a["min"], a["max"] = a2.min(0).tolist(), a2.max(0).tolist()
        accs.append(a)
        return len(accs) - 1

    meshes, materials, textures, images = [], [], [], []
    for p in parts:
        attrs = {"POSITION": add(p["V"].astype(np.float32), FLOAT, "VEC3", 34962, True),
                 "NORMAL": add(p["N"].astype(np.float32), FLOAT, "VEC3", 34962),
                 "JOINTS_0": add(p["J"].astype(np.uint16), U16, "VEC4", 34962),
                 "WEIGHTS_0": add(p["W"].astype(np.float32), FLOAT, "VEC4", 34962)}
        if p.get("C") is not None:
            attrs["COLOR_0"] = add(p["C"].astype(np.float32), FLOAT, "VEC3", 34962)
        pbr = {"baseColorFactor": [1, 1, 1, 1], "metallicFactor": p.get("metal", 0), "roughnessFactor": p.get("rough", 0.8)}
        if p.get("UV") is not None:
            attrs["TEXCOORD_0"] = add(p["UV"].astype(np.float32), FLOAT, "VEC2", 34962)
        if p.get("png"):
            while len(buf) % 4:
                buf.append(0)
            views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(p["png"])})
            buf.extend(p["png"])
            images.append({"bufferView": len(views) - 1, "mimeType": "image/png"})
            textures.append({"source": len(images) - 1, "sampler": 0})
            pbr["baseColorTexture"] = {"index": len(textures) - 1}
        ind = add(p["F"].astype(np.uint32).reshape(-1), U32, "SCALAR", 34963)
        materials.append({"name": p["name"], "doubleSided": True, "pbrMetallicRoughness": pbr})
        meshes.append({"name": p["name"], "primitives": [{"attributes": attrs, "indices": ind, "material": len(materials) - 1}]})
    ibm = np.zeros((len(names), 16), np.float32)
    ibm[:, [0, 5, 10, 15]] = 1
    ibm[:, 12:15] = -heads
    ibm_acc = add(ibm, FLOAT, "MAT4")

    M = len(parts)
    nodes = [{"name": p["name"], "mesh": i, "skin": 0} for i, p in enumerate(parts)]
    for i, n in enumerate(names):
        t = heads[i] - (heads[par[i]] if par[i] >= 0 else 0)
        nodes.append({"name": n, "translation": [round(float(v), 6) for v in t]})
    for i in range(len(names)):
        ch = [j + M for j in range(len(names)) if par[j] == i]
        if ch:
            nodes[i + M]["children"] = ch
    roots = [i + M for i in range(len(names)) if par[i] < 0]

    anims = []
    for cname, clip in clips.items():
        fr = np.arange(clip["frames"] + 1)
        tacc = add((fr / clip["fps"]).astype(np.float32), FLOAT, "SCALAR", minmax=True)
        samplers, channels = [], []
        for i, n in enumerate(names):
            if n not in clip["keys"]:
                continue
            Q = np.array([anim._interp(clip["keys"][n], f, 4) for f in fr], np.float32)
            samplers.append({"input": tacc, "output": add(Q, FLOAT, "VEC4"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": i + M, "path": "rotation"}})
        if clip.get("root"):
            r = int(roots[0]) - M
            Tt = np.array([heads[r] + anim._interp(clip["root"], f, 3) for f in fr], np.float32)
            samplers.append({"input": tacc, "output": add(Tt, FLOAT, "VEC3"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": roots[0], "path": "translation"}})
        anims.append({"name": cname, "samplers": samplers, "channels": channels})

    doc = {"asset": {"version": "2.0", "generator": "3dPazl rig"},
           "scene": 0, "scenes": [{"nodes": [*range(M), *roots]}], "nodes": nodes, "meshes": meshes, "materials": materials,
           "skins": [{"joints": list(range(M, M + len(names))), "inverseBindMatrices": ibm_acc, "skeleton": roots[0]}],
           "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": 0}]}
    if images:
        doc.update({"images": images, "textures": textures, "samplers": [{"wrapS": 10497, "wrapT": 10497, "minFilter": 9987, "magFilter": 9729}]})
    if anims:
        doc["animations"] = anims
    while len(buf) % 4:
        buf.append(0)
    doc["buffers"][0]["byteLength"] = len(buf)
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(buf))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(buf), 0x004E4942) + bytes(buf)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(out)
    return len(out)
