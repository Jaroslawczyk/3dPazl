"""Rebuild the user's Roblox avatar 1:1 with our own meshes and UVs and the original textures, then make it a 3dPazl
character (rig, clips, Roblox export).

    .venv/Scripts/python.exe scripts/rebuild_roblox_avatar.py [projects/refs/roblox_galaxy/original.glb] [name]

Steps: reference -> our frame (metres, faces +Z) -> body cut into 6 blocks, each shrinkwrapped; hair/hat and pet piece by
piece (cards for strands) -> own UV atlas (xatlas) -> original textures baked onto it -> arms raised to a T-pose bind,
the original arm angle kept as the default pose -> chars.create + accessories."""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pazl.core import chars, retopo, roblox  # noqa: E402
from pazl.paths import PROJECTS  # noqa: E402

STUD = .28  # metres per Roblox stud


def load_ref(path):
    """[(mesh in our frame, uv (trimesh, v up), PIL image)] per material, plus the transform used."""
    sc = trimesh.load(path, force="scene")
    out = []
    for node in sc.graph.nodes_geometry:
        T, key = sc.graph[node]
        g = sc.geometry[key].copy()
        g.apply_transform(T)
        mat = g.visual.material
        img = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
        out.append([g, np.asarray(g.visual.uv), img])
    lo = min(g.bounds[0][1] for g, *_ in out)
    M = trimesh.transformations.scale_matrix(STUD) @ trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0])
    M[1, 3] = -lo * STUD
    for o in out:
        o[0].apply_transform(M)
    return out


def body_parts(m):
    """Every piece of the reference body with the block it belongs to (R15-like: head, upper torso, lower torso = hips,
    arms, legs). Whole pieces are assigned by their centre, so a shoulder cap never lands in the torso and the hip piece
    that spans both legs stays one block. The upper torso is the biggest wide piece on the centre line; it gives the limits."""
    comps = m.split(only_watertight=False)
    mid = [p for p in comps if abs(p.centroid[0]) < .05]
    t = max(mid, key=lambda p: len(p.faces) * (p.bounds[0][1] < np.median(m.vertices[:, 1]) * 1.6) * (p.extents[0] > p.extents[2]))
    tw, crotch, neck = t.extents[0] / 2, t.bounds[0][1], t.bounds[1][1]
    out = []
    for p in comps:
        x, y, _ = p.centroid
        if y > neck - .02 and abs(x) < tw * .75 and p.extents[0] < tw * 1.6:
            k = "head"
        elif abs(x) > tw * .98:
            k = "arm.L" if x > 0 else "arm.R"
        elif abs(x) < .05 and p.extents[0] > tw * 1.2 and y < crotch + .06:
            k = "hips"
        elif y < crotch:
            k = "leg.L" if x >= 0 else "leg.R"
        else:
            k = "torso"
        out.append((k, p))
    return out, tw, crotch, neck


def piece_mesh(k, p):
    """Our mesh for one reference piece: round head -> icosphere; flat joint discs -> one-layer sheet; blocks -> grid box
    (resolution follows the size), all pulled onto the piece."""
    if k == "head" and len(p.faces) > 100:
        return retopo.shrinkwrap(p, 2, grow=1.3), 70
    if retopo.is_flat(p, .25):
        return retopo.sheet(p, 3), 30
    res = int(np.clip(round(5 * p.extents.max() / .5), 1, 6))  # ~2.4k triangles for the whole body, like the original
    return retopo.shrinkwrap(p, grow=1.08, box=res), 30


def textured(V, F, UV, img):
    m = trimesh.Trimesh(V, F, process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=np.c_[UV[:, 0], 1 - UV[:, 1]], material=trimesh.visual.material.PBRMaterial(baseColorTexture=img, roughnessFactor=.8, metallicFactor=0, doubleSided=True))
    return m


def build_piece(ref, uv, img, meshes, size, sharp=60):
    m = trimesh.util.concatenate(meshes)
    V, F, UV = retopo.unwrap(m, sharp)
    s = retopo.Sampler(ref, uv, img, count=1500000 if size >= 1024 else 600000)
    return V, F, UV, retopo.bake(V, F, UV, s, size)


def arm_pose(part, side):
    """(pivot, angle): pivot = top centre of the arm lowered by half its thickness; angle from straight down."""
    V = np.asarray(part.vertices)
    c = V.mean(0)
    ax = np.linalg.svd(V - c)[2][0]
    ax = ax if ax[1] < 0 else -ax  # pointing down
    top = V[:, 1].max()
    thick = np.ptp(V[V[:, 1] < top - (top - V[:, 1].min()) * .5][:, 0]) if len(V) else .1
    y = top - thick / 2  # the joint: on the arm's own axis, half a thickness below its top
    piv = c + ax * ((y - c[1]) / ax[1])
    return piv, float(np.degrees(np.arctan2(abs(ax[0]), -ax[1]))), thick


def main(src="projects/refs/roblox_galaxy/original.glb", name="galaxy_1to1"):
    out = PROJECTS / "refs" / Path(src).parent.name / "rebuild"
    out.mkdir(parents=True, exist_ok=True)
    refs = load_ref(ROOT / src)
    refs.sort(key=lambda r: -len(r[0].faces))  # body, hair+hat, pet
    (body, buv, bimg), (hair, huv, himg), (pet, puv, pimg) = refs[:3]

    plist, tw, crotch, neck = body_parts(body)
    pieces, owner = [], []
    for k, p in plist:  # shading split at 30 deg on blocks, 70 on the round head
        m, ang = piece_mesh(k, p)
        pieces.append(trimesh.graph.smooth_shade(m, angle=np.radians(ang)))
        owner.append(np.full(len(pieces[-1].vertices), k, object))
    parts = {k: trimesh.util.concatenate([p for kk, p in plist if kk == k]) for k in {k for k, _ in plist}}
    V, F, UV, tex = build_piece(body, buv, bimg, pieces, 1024, sharp=None)
    owner = np.concatenate(owner)
    m_all = trimesh.util.concatenate(pieces)
    from scipy.spatial import cKDTree
    who = owner[cKDTree(m_all.vertices).query(V)[1]]
    textured(V, F, UV, tex).export(out / "body_pose.glb")  # as in the reference, for comparing

    Vt = V.copy()
    rest, pivots = {}, {}
    for side, k in (("L", 1), ("R", -1)):
        piv, ang, thick = arm_pose(parts["arm." + side], side)
        R = trimesh.transformations.rotation_matrix(np.radians(k * (90 - ang)), [0, 0, 1], piv)
        sel = who == "arm." + side
        Vt[sel] = trimesh.transform_points(V[sel], R)
        q = trimesh.transformations.quaternion_from_matrix(np.linalg.inv(R))  # w, x, y, z
        rest["upper_arm." + side] = [float(q[1]), float(q[2]), float(q[3]), float(q[0])]
        pivots[side] = piv
        print(f"arm.{side}: {ang:.1f} deg from vertical, pivot {np.round(piv, 3)}")
    textured(Vt, F, UV, tex).export(out / "body_t.glb")
    bone = {"head": "head", "torso": "chest", "hips": "hips", "arm.L": "upper_arm.L", "arm.R": "upper_arm.R", "leg.L": "thigh.L", "leg.R": "thigh.R"}
    np.savez_compressed(out / "body_t.labels.npz", P=Vt, bone=np.array([bone[w] for w in who]))  # which bone each block follows

    hV, hF, hUV, htex = build_piece(hair, huv, himg, [retopo.rebuild(hair)], 512)
    textured(hV, hF, hUV, htex).export(out / "hair_hat.glb")
    pV, pF, pUV, ptex = build_piece(pet, puv, pimg, [retopo.rebuild(pet)], 256)
    textured(pV, pF, pUV, ptex).export(out / "pet.glb")
    sc = trimesh.Scene([trimesh.load(out / f, force="mesh") for f in ("body_pose.glb", "hair_hat.glb", "pet.glb")])
    sc.export(out / "posed_all.glb")  # whole figure in the reference pose, to compare in the app
    print("tris body", len(F), "hair+hat", len(hF), "pet", len(pF), "total", len(F) + len(hF) + len(pF))

    rel = (out / "body_t.glb").relative_to(PROJECTS).as_posix()
    chars.create(name, src=rel, template="humanoid", crotch=float(crotch), torso=float(tw), quality="ultra")
    from pazl.core import rig
    rg = rig.load(chars._rn(name))
    for b in rg["bones"]:  # the arm turns about the same point it was raised about, so the default pose is the reference one
        for side, piv in pivots.items():
            if b["name"] == "upper_arm." + side:
                b["head"] = [float(v) for v in piv]
            if b["name"] == "shoulder." + side:
                b["tail"] = [float(v) for v in piv]
    rig.save(rg)
    c = chars.load(name)
    c["rest_pose"] = rest
    c["labels"] = (out / "body_t.labels.npz").relative_to(PROJECTS).as_posix()
    c["outfit"] = [{"kind": "acc_head", "file": (out / "hair_hat.glb").relative_to(PROJECTS).as_posix()},
                   {"kind": "acc_chest", "file": (out / "pet.glb").relative_to(PROJECTS).as_posix()}]
    chars.save(c)
    r = chars.export(name)
    print("character", r["path"], r["tris"], "tris")
    print(roblox.export_char(name)["files"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
