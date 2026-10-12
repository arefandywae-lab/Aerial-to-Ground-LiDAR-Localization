"""Which difference explains CPU-painter vs GPU-z-buffer id mismatch: painter's approximation, or float32 rounding?
Reference = exact float64 z-buffer on CPU (sort far->near, last write wins). CPU only; run inside WSL."""
import sys

import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1
from harness import load_session

s = load_session("/root/data/s0_img")
d = np.load(m1.LIDAR_MAP)
P, rgb, K = d["pts"].astype(np.float64), d["rgb"], s["K"]


def exact_zbuf(T, size=(640, 480), dtype=np.float64):
    w, h = size
    Pq = P.astype(dtype)
    pc = (Pq - T[:3, 3].astype(dtype)) @ T[:3, :3].astype(dtype)
    z = pc[:, 2]
    vis = np.where((z > 0.5) & (z < 25))[0]
    zv = z[vis]
    u = np.round(dtype(K[0, 0]) * pc[vis, 0] / zv + dtype(K[0, 2])).astype(int)
    v = np.round(dtype(K[1, 1]) * pc[vis, 1] / zv + dtype(K[1, 2])).astype(int)
    r = np.clip(np.round(dtype(K[0, 0]) * m1.SPLAT_M / zv), 0, 4).astype(int)
    ids = np.full((h, w), -1, np.int32)
    zb = np.full((h, w), np.inf)
    for du in range(-4, 5):
        for dv in range(-4, 5):
            m = np.where(r >= max(abs(du), abs(dv)))[0]
            uu, vv = u[m] + du, v[m] + dv
            ok = (uu >= 0) & (uu < w) & (vv >= 0) & (vv < h)
            m, uu, vv = m[ok], uu[ok], vv[ok]
            o = np.argsort(-zv[m], kind="stable")
            m, uu, vv = m[o], uu[o], vv[o]
            nearer = zv[m] <= zb[vv, uu]
            ids[vv[nearer], uu[nearer]] = vis[m[nearer]]
            zb[vv[nearer], uu[nearer]] = zv[m[nearer]]
    return ids


for i in (10, 60, 120):
    T = s["T"][i]
    ref = exact_zbuf(T)
    _, painter = m1.render(P, rgb, T, K)  # includes hole fill; compare only unfilled-by-both below
    ref_f = m1.shade(ref.copy(), rgb)[1]
    f32 = m1.shade(exact_zbuf(T, dtype=np.float32), rgb)[1]
    both = (ref_f >= 0) & (painter >= 0)
    both32 = (ref_f >= 0) & (f32 >= 0)
    print(f"pose {i}: painter==exact {np.mean(painter[both] == ref_f[both]):.3f} | float32==float64 (same algorithm) {np.mean(f32[both32] == ref_f[both32]):.3f}")
