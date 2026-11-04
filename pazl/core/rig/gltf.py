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

    attrs = {"POSITION": add(V.astype(np.float32), FLOAT, "VEC3", 34962, True),
             "NORMAL": add(N.astype(np.float32), FLOAT, "VEC3", 34962),
             "JOINTS_0": add(joints.astype(np.uint16), U16, "VEC4", 34962),
             "WEIGHTS_0": add(weights.astype(np.float32), FLOAT, "VEC4", 34962)}
    if C is not None:
        attrs["COLOR_0"] = add(C.astype(np.float32), FLOAT, "VEC3", 34962)
    ind = add(F.astype(np.uint32).reshape(-1), U32, "SCALAR", 34963)
    ibm = np.zeros((len(names), 16), np.float32)
    ibm[:, [0, 5, 10, 15]] = 1
    ibm[:, 12:15] = -heads
    ibm_acc = add(ibm, FLOAT, "MAT4")

    nodes = [{"name": "Body", "mesh": 0, "skin": 0}]
    for i, n in enumerate(names):
        t = heads[i] - (heads[par[i]] if par[i] >= 0 else 0)
        nodes.append({"name": n, "translation": [round(float(v), 6) for v in t]})
    for i in range(len(names)):
        ch = [j + 1 for j in range(len(names)) if par[j] == i]
        if ch:
            nodes[i + 1]["children"] = ch
    roots = [i + 1 for i in range(len(names)) if par[i] < 0]

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
            channels.append({"sampler": len(samplers) - 1, "target": {"node": i + 1, "path": "rotation"}})
        if clip.get("root"):
            r = int(roots[0]) - 1
            Tt = np.array([heads[r] + anim._interp(clip["root"], f, 3) for f in fr], np.float32)
            samplers.append({"input": tacc, "output": add(Tt, FLOAT, "VEC3"), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": roots[0], "path": "translation"}})
        anims.append({"name": cname, "samplers": samplers, "channels": channels})

    doc = {"asset": {"version": "2.0", "generator": "3dPazl rig"},
           "scene": 0, "scenes": [{"nodes": [0, *roots]}], "nodes": nodes,
           "meshes": [{"name": "Body", "primitives": [{"attributes": attrs, "indices": ind, "material": 0}]}],
           "materials": [{"name": "body", "doubleSided": True, "pbrMetallicRoughness": {
               "baseColorFactor": [1, 1, 1, 1], "metallicFactor": 0, "roughnessFactor": 0.8}}],
           "skins": [{"joints": list(range(1, len(names) + 1)), "inverseBindMatrices": ibm_acc, "skeleton": roots[0]}],
           "accessors": accs, "bufferViews": views, "buffers": [{"byteLength": 0}]}
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
