"""Offline stand-in for the closed loop (no Gazebo): replay a recorded ground session through the SAME online logic as ros/closed_loop.py - the localizer's position prior is the
filter's own estimate, the filter predicts with noisy GT-derived odometry and updates with the PnP pose. The robot is not steered by the estimate here (it follows the recording).
usage: replay_online.py QUERY_SESSION OUT.npz [step=2]   env as vps/m1lf.py + SEED"""
import math, os, sys
import cv2, numpy as np
sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1lf
from harness import load_session
from mcl import MCL, wrap

q = load_session(sys.argv[1]); step = int(sys.argv[3]) if len(sys.argv) > 3 else 2
rng = np.random.default_rng(int(os.environ.get("SEED", 0)))
M = m1lf.Method(); M.prepare("/root/data/ud0_img")
def base(T):  # base pose (x, y, heading) from the camera pose (camera 0.3 m ahead of the base)
    h = math.atan2(T[1, 2], T[0, 2]); return np.array([T[0, 3] - 0.3 * math.cos(h), T[1, 3] - 0.3 * math.sin(h), h])
G = [base(T) for T in q["T"]]
f = MCL(G[0][:2], G[0][2], seed=int(os.environ.get("SEED", 0)))
rows, prev = [], G[0]
for i in range(step, len(G), step):
    g = G[i]; c, s = math.cos(prev[2]), math.sin(prev[2]); d = g[:2] - prev[:2]
    rel = np.array([c * d[0] + s * d[1], -s * d[0] + c * d[1]]); dist = float(np.hypot(*rel))
    f.predict(rel * (1 + rng.normal(0, 0.01)) + rng.normal(0, 0.002, 2), float(wrap(g[2] - prev[2])) + math.radians(rng.normal(0, 0.1 * dist + 0.02)))
    prev = g
    prior = f.mean()[:2] if f.spread() < 10 else None
    T, info = M.localize(cv2.imread(q["images"][i]), q["K"], prior_xy=prior)
    obs_err, rej = np.nan, False
    if T is not None and info.get("inliers", 0) >= 12:
        o = base(T); obs_err = float(np.linalg.norm(o[:2] - g[:2])); rej = not f.update(o, info["inliers"])
    e = f.mean()
    rows.append((i, *g, *e, f.spread(), obs_err, info.get("inliers", 0), float(prior is None), float(rej)))
    if len(rows) % 20 == 0:
        print(f"frame {i}: gt=({g[0]:.1f},{g[1]:.1f}) est=({e[0]:.1f},{e[1]:.1f}) spread={f.spread():.2f} obs_err={obs_err:.2f} prior={'none' if prior is None else 'filter'}", flush=True)
r = np.array(rows); err = np.linalg.norm(r[:, 4:6] - r[:, 1:3], axis=1)
np.savez(sys.argv[2], rows=r)
print(f"REPLAY frames {len(r)} | est error median {np.median(err):.2f} m p95 {np.percentile(err,95):.2f} m max {err.max():.1f} m | >5 m: {np.mean(err>5):.1%} | observations >5 m wrong: {np.nanmean(r[:,8]>5):.1%} | frames without prior {r[:,10].mean():.1%} | rejected by gate {r[:,11].mean():.1%} | spread<0.7: {np.mean(r[:,7]<0.7):.0%}")
