"""Compare a reference GLB with ours in one short table: triangles (total and per mesh), size, proportions and the
silhouette width at 10 heights, all scaled to the model height so files in studs, metres or cm compare directly.

    .venv/Scripts/python.exe -I scripts/glb_compare.py REF.glb MINE.glb

Read the "worse" lines first: they are the mistakes to fix (too many triangles, wrong proportions)."""
import sys

import numpy as np
import trimesh


def load(path):
    sc = trimesh.load(path, force="scene")
    parts = []
    for node in sc.graph.nodes_geometry:
        T, key = sc.graph[node]
        g = sc.geometry[key]
        if not hasattr(g, "faces"):
            continue
        g = g.copy()
        g.apply_transform(T)
        parts.append((key, g))
    V = np.vstack([g.vertices for _, g in parts])
    return parts, V


def profile(V, n=10):
    lo, hi = V.min(0), V.max(0)
    H = hi[1] - lo[1]
    y = (V[:, 1] - lo[1]) / H
    out = []
    for i in range(n):
        m = (y >= i / n) & (y < (i + 1) / n + 1e-9)
        out.append((V[m, 0].max() - V[m, 0].min()) / H if m.any() else 0)
    return out


def main(ref, mine):
    rows = {}
    for tag, path in (("ref", ref), ("mine", mine)):
        parts, V = load(path)
        lo, hi = V.min(0), V.max(0)
        size = hi - lo
        rows[tag] = {"tris": sum(len(g.faces) for _, g in parts), "parts": [(k, len(g.faces)) for k, g in parts], "size": size,
                     "ratio": size / size[1], "prof": profile(V)}
    r, m = rows["ref"], rows["mine"]
    print(f"{'':14}{'ref':>12}{'mine':>12}")
    print(f"{'triangles':14}{r['tris']:>12,}{m['tris']:>12,}   x{m['tris'] / max(r['tris'], 1):.1f}" + ("  worse" if m["tris"] > r["tris"] * 1.3 else ""))
    print(f"{'size (raw)':14}{'x'.join(f'{v:.2f}' for v in r['size']):>12}{'x'.join(f'{v:.2f}' for v in m['size']):>12}")
    for i, ax in enumerate("XYZ"):
        if ax == "Y":
            continue
        d = m["ratio"][i] / r["ratio"][i]
        print(f"{ax + '/height':14}{r['ratio'][i]:>12.2f}{m['ratio'][i]:>12.2f}   {d:.2f}" + ("  worse" if abs(d - 1) > .15 else ""))
    if (r["ratio"][0] < .8) != (m["ratio"][0] < .8):
        print("pose differs (T-pose vs arms down): ignore X/height and the arm bands, compare the leg and head bands")
    print("width/height by height band (0 = feet):")
    for i, (a, b) in enumerate(zip(r["prof"], m["prof"])):
        print(f"  {i / 10:.1f}-{(i + 1) / 10:.1f} {a:>10.2f}{b:>12.2f}" + ("  worse" if a and abs(b / a - 1) > .2 else ""))
    for tag in ("ref", "mine"):
        print(f"{tag} meshes: " + ", ".join(f"{k} {t}" for k, t in sorted(rows[tag]["parts"], key=lambda x: -x[1])[:12]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
