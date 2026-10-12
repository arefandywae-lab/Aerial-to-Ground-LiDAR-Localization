"""Test of the idea "weight PnP residuals by depth" (near points trusted more than far structure) on the stored route-2 correspondences (CPU only; seq_collect.py output).
For every frame with a pose, the 6-DoF pose is re-solved from the SAME inlier correspondences with residual scale s_i = (d_i / 10 m)^(-k/2) (k = 0 is the unweighted baseline; k = 1, 2 down-weight far points), or with far points removed (d > Dmax).
Initial pose = the stored PnP pose; Huber loss, 2 px. Metrics over frames with a pose and over the gate >= 80 inliers subset.
usage: pnp_weight_test.py SEQ.npz"""
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

d = np.load(sys.argv[1])  # plain arrays (seq_collect.py), no pickle
P, G, K, inl, off = d["poses"], d["gt"], d["K"], d["inl"], d["off"]
p2 = [d["p2"][off[i]:off[i + 1]] for i in range(len(off) - 1)]
p3 = [d["p3"][off[i]:off[i + 1]] for i in range(len(off) - 1)]


def err(T, Tg):
    c = np.clip((np.trace(T[:3, :3].T @ Tg[:3, :3]) - 1) / 2, -1, 1)
    return np.linalg.norm(T[:3, 3] - Tg[:3, 3]), np.degrees(np.arccos(c))


def solve(t, k, dmax):
    T0 = P[t]
    Xc = (p3[t] - T0[:3, 3]) @ T0[:3, :3]
    dep = Xc[:, 2]
    keep = (dep > 0.5) & (dep < dmax)
    if keep.sum() < 12:
        return None
    a2, a3, dd = p2[t][keep], p3[t][keep], dep[keep]
    s = (dd / 10.0) ** (-k / 2.0)

    def res(x):
        R = Rot.from_rotvec(x[:3]).as_matrix()
        Xcam = (a3 - x[3:]) @ R
        z = np.maximum(Xcam[:, 2], 1e-3)
        r = np.c_[K[0, 0] * Xcam[:, 0] / z + K[0, 2], K[1, 1] * Xcam[:, 1] / z + K[1, 2]] - a2
        return (r * s[:, None]).ravel()

    x0 = np.r_[Rot.from_matrix(T0[:3, :3]).as_rotvec(), T0[:3, 3]]
    sol = least_squares(res, x0, loss="huber", f_scale=2.0 * float(np.median(s)), max_nfev=40)
    T = np.eye(4)
    T[:3, :3] = Rot.from_rotvec(sol.x[:3]).as_matrix()
    T[:3, 3] = sol.x[3:]
    return T


frames = [t for t in range(len(G)) if np.isfinite(P[t, 0, 0]) and len(p2[t]) >= 12]
print(f"{len(frames)} frames with a stored pose; route 2, prior 5 m settings")
variants = (("unweighted (stored PnP pose)", None, None), ("re-solve, k=0 (no weights)", 0, 1e9), ("k=1 (w ~ 1/d)", 1, 1e9), ("k=2 (w ~ 1/d^2)", 2, 1e9),
            ("k=0, drop points beyond 25 m", 0, 25), ("k=0, drop points beyond 15 m", 0, 15), ("k=2, drop points beyond 25 m", 2, 25))
res = {}
for name, k, dmax in variants:
    res[name] = {}
    for t in frames:
        T = P[t] if k is None else solve(t, k, dmax)
        if T is not None:
            res[name][t] = (*err(T, G[t]), inl[t])


def stat(rows):
    r = np.array(rows)
    g = r[:, 2] >= 80
    f = lambda m: (np.mean((r[m, 0] <= 1) & (r[m, 1] <= 5)), np.mean((r[m, 0] <= .5) & (r[m, 1] <= 5)), np.median(r[m, 0]))
    a, b = f(np.ones(len(r), bool)), f(g)
    return len(r), a, b, np.mean((r[:, 0] > 5) | (r[:, 1] > 10))


print("PAIRED: every variant is compared with the stored pose on exactly the frames it could solve")
print(f"{'variant':34s} {'frames':>6s} | all: within(1m,5deg) within(0.5m,5deg) median | gate>=80: within(1m,5deg) within(0.5m,5deg) median | gross-wrong (variant vs stored)")
for name, k, dmax in variants[1:]:
    ts = sorted(res[name])
    n, a, b, w = stat([res[name][t] for t in ts])
    n0, a0, b0, w0 = stat([res[variants[0][0]][t] for t in ts])
    print(f"{name:34s} {n:6d} | {a[0]:6.1%} {a[1]:6.1%} {a[2]:6.3f} m | {b[0]:6.1%} {b[1]:6.1%} {b[2]:6.3f} m | {w:5.1%} vs {w0:5.1%}")
    print(f"{'   stored pose, same frames':34s} {n0:6d} | {a0[0]:6.1%} {a0[1]:6.1%} {a0[2]:6.3f} m | {b0[0]:6.1%} {b0[1]:6.1%} {b0[2]:6.3f} m |")
