"""Why do wrong poses have many inliers? Uses per-query results only (CPU). columns of *_err.npy: dt, dr, inliers."""
import sys

import numpy as np

S = np.load("/root/data/s0_img/poses.npy")
Q = np.load("/root/data/q1_img/poses.npy")
e = np.load(sys.argv[1])
dt, dr, inl = e[:, 0], e[:, 1], e[:, 2]
ret = np.isfinite(dt)
wrong = ret & ((dt > 5) | (dr > 10))
good = ret & (dt <= 0.25) & (dr <= 2)
mid = ret & ~wrong & ~good
near = np.array([np.linalg.norm(S[:, :3, 3] - q[:3, 3], axis=1).min() for q in Q])
print(f"returned {ret.sum()} | good(<=.25m,2deg) {good.sum()} | mid {mid.sum()} | wrong(>5m or >10deg) {wrong.sum()}")
for name, m in (("good", good), ("mid", mid), ("wrong", wrong)):
    if m.any():
        print(f"{name:5s} inliers med {np.median(inl[m]):.0f} p10 {np.percentile(inl[m],10):.0f} p90 {np.percentile(inl[m],90):.0f} | query->map dist med {np.median(near[m]):.2f} m | pos err med {np.median(dt[m]):.2f} m rot err med {np.median(dr[m]):.1f} deg")
# are wrong poses a position problem, a rotation problem, or both?
print("wrong: pos>5m", int((dt[wrong] > 5).sum()), "| rot>10deg", int((dr[wrong] > 10).sum()), "| both", int(((dt[wrong] > 5) & (dr[wrong] > 10)).sum()))
# along the query sequence: are failures clustered (specific places) or scattered?
idx = np.where(wrong)[0]
runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1) if len(idx) else []
print("wrong-query runs (start-end):", [(int(r[0]), int(r[-1])) for r in runs])
print("not returned at:", np.where(~ret)[0].tolist()[:40])
