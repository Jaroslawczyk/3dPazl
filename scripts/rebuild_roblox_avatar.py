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


def build_piece(ref, uv, img, meshes, size, sharp=60, max_hole=20, body=None):
    from pazl.core import meshcheck
    m = trimesh.util.concatenate(meshes)
    if body is not None:  # out of the head before texturing, so nothing gets squashed later
        m = meshcheck.push_out_faces(m, body)
    m.merge_vertices()  # unwrap (smooth_shade) welds like this: clean must see the same triangles
    for _ in range(3):  # a fill can leave a new needle on a nearly straight border: repeat
        m = meshcheck.clean(m, max_hole=max_hole, scale=6)  # no slivers or small gaps (mesh_check uses the 1.9 m diagonal: 3x margin for float32 saving)
    V, F, UV = retopo.unwrap(m, sharp)
    UV[:, 1] = 1 - UV[:, 1]  # xatlas gives v up; glTF wants v down (otherwise every island is mirrored)
    s = retopo.Sampler(ref, uv, img, count=1500000 if size >= 1024 else 600000)
    return V, F, UV, retopo.bake(V, F, UV, s, size)


def measure(S, y0, y1):
    """(cx, cz, hx, hz) of the reference samples S (part's local frame) with local y between y0 and y1."""
    lo, hi = min(y0, y1), max(y0, y1)
    sel = S[(S[:, 1] >= lo) & (S[:, 1] <= hi)]
    if len(sel) < 20:
        sel = S[np.argsort(np.abs(S[:, 1] - (lo + hi) / 2))[:200]]
    a, b = np.percentile(sel, 3, 0), np.percentile(sel, 97, 0)
    return (a[0] + b[0]) / 2, (a[2] + b[2]) / 2, (b[0] - a[0]) / 2, (b[2] - a[2]) / 2


def segment(S, frame, y_top, y_bot, k=3, n=12, power=6.0):
    """One R15 part: k measured rings from y_top down to y_bot in the frame -> loft."""
    L = y_top - y_bot
    rings = []
    for f in np.linspace(0, 1, k):
        y = y_top - L * f
        band = L * .14
        rings.append((y, *measure(S, y - band if f == 0 else y - band / 2, y + band if f == 1 else y + band / 2)))
    return retopo.loft(frame, rings, n, power)


def limb_frame(mesh, down):
    """Local frame of a limb: origin at its top centre, local -Y along `down`, +Z towards the front."""
    d = down / np.linalg.norm(down)
    Y = -d
    Z = np.array([0, 0, 1.]) - Y * Y[2]
    Z /= np.linalg.norm(Z)
    X = np.cross(Y, Z)
    V = np.asarray(mesh.vertices)
    t = (V - V.mean(0)) @ d
    o = V.mean(0) + d * t.min()
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = X, Y, Z, o
    return M, d, float(t.max() - t.min())


def joints(pieces, o, d, L):
    """Positions along a limb (0 = top, L = bottom) of its flat joint discs, clustered."""
    ts = sorted(float((p.centroid - o) @ d) for p in pieces if retopo.is_flat(p, .25) and len(p.faces) > 24)
    out = []
    for t in ts:
        if out and t - out[-1][-1] < .06:
            out[-1].append(t)
        else:
            out.append([t])
    return [float(np.mean(c)) for c in out if .05 * L < np.mean(c) < .95 * L]


def r15_body(body, plist):
    """The body as 15 clean aligned parts like Roblox R15, each a loft of rings measured on the reference.
    Returns [(bone, mesh, islands)], joints {bone: (head, tail)} in the reference pose, arm data for the T-pose."""
    groups = {k: [p for kk, p in plist if kk == k] for k in {k for k, _ in plist}}
    out, J, arms = [], {}, {}
    for k, bone, power, n in (("torso", "chest", 6.0, 16), ("hips", "hips", 6.0, 16), ("head", "head", 2.4, 20)):
        m = trimesh.util.concatenate(groups[k])
        S = trimesh.sample.sample_surface(m, 40000, seed=2)[0]
        y0, y1 = m.bounds[1][1], m.bounds[0][1]
        out.append((bone, *segment(S, np.eye(4), y0, y1, 7 if k == "head" else 5, n, power)))
    for side in ("L", "R"):
        for limb, names in (("arm", ("upper_arm", "forearm", "hand")), ("leg", ("thigh", "shin", "foot"))):
            ps = groups[f"{limb}.{side}"]
            m = trimesh.util.concatenate(ps)
            if limb == "arm":
                V = np.asarray(m.vertices)
                d = np.linalg.svd(V - V.mean(0))[2][0]
                d = d if d[1] < 0 else -d
            else:
                d = np.array([0, -1., 0])
            M, d, L = limb_frame(m, d)
            o = M[:3, 3]
            S = trimesh.transform_points(trimesh.sample.sample_surface(m, 40000, seed=3)[0], np.linalg.inv(M))
            js = joints(ps, o, d, L)
            if limb == "arm":
                cut = [js[0] if js else .43 * L, .88 * L]
            else:
                cut = js[:2] if len(js) >= 2 else [.53 * L, .81 * L]
            cuts = [0.0, *sorted(cut), L]
            for i, nm in enumerate(names):
                mesh, isl = segment(S, M, -cuts[i], -cuts[i + 1], 3, 12, 6.0)
                out.append((f"{nm}.{side}", mesh, isl))
                J[f"{nm}.{side}"] = (o + d * cuts[i], o + d * cuts[i + 1])
            if limb == "arm":
                hx = measure(S, -L * .1, 0)[2]
                arms[side] = (o + d * hx, float(np.degrees(np.arctan2(abs(d[0]), -d[1]))))
    return out, J, arms


def main(src="projects/refs/roblox_galaxy/original.glb", name="galaxy_1to1"):
    out = PROJECTS / "refs" / Path(src).parent.name / "rebuild"
    out.mkdir(parents=True, exist_ok=True)
    refs = load_ref(ROOT / src)
    refs.sort(key=lambda r: -len(r[0].faces))  # body, hair+hat, pet
    (body, buv, bimg), (hair, huv, himg), (pet, puv, pimg) = refs[:3]

    plist, tw, crotch, neck = body_parts(body)
    parts, J, arms = r15_body(body, plist)
    meshes, islands, bones, off = [], [], [], 0
    for bone, m, isl in parts:
        meshes.append(m)
        islands += [(ids + off, uv, wh) for ids, uv, wh in isl]
        bones += [bone] * len(m.vertices)
        off += len(m.vertices)
    mb = trimesh.util.concatenate(meshes)
    V, F, who = np.asarray(mb.vertices), np.asarray(mb.faces), np.array(bones)
    UV = retopo.pack(islands, 1024)
    tex = retopo.bake(V, F, UV, retopo.Sampler(body, buv, bimg, count=1500000), 1024)
    textured(V, F, UV, tex).export(out / "body_pose.glb")  # as in the reference, for comparing

    Vt = V.copy()
    rest, Jt = {}, dict(J)
    for side, k in (("L", 1), ("R", -1)):
        piv, ang = arms[side]
        R = trimesh.transformations.rotation_matrix(np.radians(k * (90 - ang)), [0, 0, 1], piv)
        sel = np.array([w.endswith("." + side) and w.split(".")[0] in ("upper_arm", "forearm", "hand") for w in who])
        Vt[sel] = trimesh.transform_points(V[sel], R)
        for nm in ("upper_arm", "forearm", "hand"):
            Jt[f"{nm}.{side}"] = tuple(trimesh.transform_points(np.array(J[f"{nm}.{side}"]), R))
        Jt[f"upper_arm.{side}"] = (trimesh.transform_points([piv], R)[0], Jt[f"upper_arm.{side}"][1])
        q = trimesh.transformations.quaternion_from_matrix(np.linalg.inv(R))  # w, x, y, z
        rest["upper_arm." + side] = [float(q[1]), float(q[2]), float(q[3]), float(q[0])]
        print(f"arm.{side}: {ang:.1f} deg from vertical, shoulder {np.round(piv, 3)}")
    textured(Vt, F, UV, tex).export(out / "body_t.glb")
    np.savez_compressed(out / "body_t.labels.npz", P=Vt, bone=who)  # which bone each part follows

    head_c = trimesh.util.concatenate([p for k, p in plist if k == "head"]).bounds.mean(0)
    hV, hF, hUV, htex = build_piece(hair, huv, himg, [retopo.rebuild(hair, root_near=head_c)], 512, max_hole=8, body=trimesh.Trimesh(V, F, process=False))
    textured(hV, hF, hUV, htex).export(out / "hair_hat.glb")
    pV, pF, pUV, ptex = build_piece(pet, puv, pimg, [retopo.rebuild(pet)], 256, body=trimesh.Trimesh(V, F, process=False))
    textured(pV, pF, pUV, ptex).export(out / "pet.glb")
    sc = trimesh.Scene([trimesh.load(out / f, force="mesh") for f in ("body_pose.glb", "hair_hat.glb", "pet.glb")])
    sc.export(out / "posed_all.glb")  # whole figure in the reference pose, to compare in the app
    print("tris body", len(F), "hair+hat", len(hF), "pet", len(pF), "total", len(F) + len(hF) + len(pF))

    rel = (out / "body_t.glb").relative_to(PROJECTS).as_posix()
    chars.create(name, src=rel, template="humanoid", crotch=float(crotch), torso=float(tw), quality="ultra")
    from pazl.core import rig
    rg = rig.load(chars._rn(name))
    for b in rg["bones"]:  # every part turns about its own joint (R15 style): elbows and knees bend without gaps
        if b["name"] in Jt:
            h, t = Jt[b["name"]]
            b["head"], b["tail"] = [float(v) for v in h], [float(v) for v in t]
        side = b["name"][-2:]
        if b["name"].startswith("shoulder") and f"upper_arm{side}" in Jt:
            b["tail"] = [float(v) for v in Jt[f"upper_arm{side}"][0]]
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
