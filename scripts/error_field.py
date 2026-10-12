"""Is the ~0.5 m translation error of the urban poses noise or a slowly varying bias (map-frame misalignment against the GT world)?
Uses saved predictions (*_pred.npy) and GT poses of the query session. For accepted poses (inliers >= GATE):
 1. error vector (pred - GT, world xyz): mean and per-axis spread
 2. the same vector in the QUERY camera frame (x right, y down, z forward): is it along the viewing direction?
 3. spatial smoothness: for each pose compare its error vector with the mean of its neighbours within RADIUS m (excluding itself); residual after removing that local mean
usage: error_field.py PREFIX QUERY_SESSION_DIR [gate=80] [radius=12]"""
import sys

import numpy as np

pre, sess = sys.argv[1], sys.argv[2]
gate = float(sys.argv[3]) if len(sys.argv) > 3 else 80
R = float(sys.argv[4]) if len(sys.argv) > 4 else 12
P = np.load(pre + "_pred.npy")
G = np.load(sess + "/poses.npy")
e = np.load(pre + "_err.npy")
ok = np.isfinite(P[:, 0, 0]) & (e[:, 2] >= gate) & (e[:, 0] < 5)  # accepted and not gross-wrong
d = P[ok, :3, 3] - G[ok, :3, 3]
Rg = G[ok, :3, :3]
dc = np.einsum("nji,nj->ni", Rg, d)  # error expressed in the GT camera frame
pos = G[ok, :3, 3]
print(f"{ok.sum()} accepted poses (gate {gate:.0f}, gross errors excluded)")
print("world-frame error mean %s  std %s  | |mean| %.3f m, median |err| %.3f m" % (d.mean(0).round(3), d.std(0).round(3), np.linalg.norm(d.mean(0)), np.median(np.linalg.norm(d, axis=1))))
print("camera-frame error (x right, y down, z forward): mean %s  std %s  | share of squared error along the viewing axis %.0f %%" % (
    dc.mean(0).round(3), dc.std(0).round(3), 100 * (dc[:, 2] ** 2).sum() / (dc ** 2).sum()))
res = np.zeros_like(d)
cnt = 0
for i in range(len(d)):
    m = (np.linalg.norm(pos[:, :2] - pos[i, :2], axis=1) < R) & (np.arange(len(d)) != i)
    if m.sum() >= 3:
        res[i] = d[i] - d[m].mean(0)
        cnt += 1
    else:
        res[i] = np.nan
v = np.isfinite(res[:, 0])
print(f"after removing the local mean of the other poses within {R:.0f} m ({int(v.sum())} poses have >= 3 neighbours): median |residual| {np.median(np.linalg.norm(res[v], axis=1)):.3f} m (was {np.median(np.linalg.norm(d[v], axis=1)):.3f} m)")
# coarse map of the bias: mean error vector per 25 m cell
cells = {}
for p, v_ in zip(pos, d):
    cells.setdefault((int(np.floor(p[0] / 25)), int(np.floor(p[1] / 25))), []).append(v_)
print("mean world error per 25 m cell (cell x,y -> n, mean dx dy dz):")
for k in sorted(cells):
    a = np.array(cells[k])
    if len(a) >= 3:
        print(f"  {k}: n={len(a):3d}  {a.mean(0).round(2)}  std {a.std(0).round(2)}")
