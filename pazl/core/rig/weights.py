"""Automatic skin weights: inverse distance to bone segments, restricted to nearby bones, then diffused along
the mesh surface (Laplacian smoothing over welded vertices), top-4 influences, normalized."""
from __future__ import annotations

import numpy as np
from scipy import sparse


def seg_dist(V, A, B):
    """Distances (n, m) from points V to segments A[j]-B[j]."""
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    t = np.clip(((V[:, None, :] - A[None]) * AB[None]).sum(2) / L2, 0, 1)
    P = A[None] + t[..., None] * AB[None]
    return np.linalg.norm(V[:, None, :] - P, axis=2)


def weld(V, tol=1e-5):
    key = np.round(V / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return first, inv.reshape(-1)


def compute(V, F, heads, tails, smooth=4, alpha=0.5, max_inf=4):
    first, inv = weld(V)
    U = V[first]
    n, m = len(U), len(heads)
    D = seg_dist(U, heads, tails)
    dmin = D.min(1, keepdims=True)
    W = 1.0 / np.maximum(D, 1e-4) ** 4
    W[D > dmin * 1.3 + 0.01 * np.ptp(V, 0).max()] = 0
    W /= W.sum(1, keepdims=True)
    if smooth and len(F):
        f = inv[F]
        i = np.concatenate([f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]])
        j = np.concatenate([f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]])
        A = sparse.csr_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
        A.data[:] = 1
        deg = np.asarray(A.sum(1)).ravel()
        Dinv = sparse.diags(np.where(deg > 0, 1 / np.maximum(deg, 1), 0))
        An = Dinv @ A
        has = deg > 0
        for _ in range(smooth):
            S = An @ W
            W[has] = (1 - alpha) * W[has] + alpha * S[has]
    J = np.argsort(-W, axis=1)[:, :max_inf]
    Wk = np.take_along_axis(W, J, 1)
    Wk[Wk < 0.01] = 0
    s = Wk.sum(1, keepdims=True)
    Wk = np.where(s > 0, Wk / np.maximum(s, 1e-12), 0)
    return J[inv].astype(np.uint16), Wk[inv].astype(np.float32)


def stats(joints, weights, names):
    dom = joints[np.arange(len(joints)), np.argmax(weights, 1)]
    cnt = np.bincount(dom, minlength=len(names))
    return {"verts": int(len(weights)), "unweighted": int((weights.sum(1) < 0.5).sum()),
            "avg_influences": round(float((weights > 0).sum(1).mean()), 2),
            "empty_bones": [names[i] for i in range(len(names)) if cnt[i] == 0]}
