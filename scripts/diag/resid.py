"""Residual failures of a run: counts, mirror signature, and where along the query path they occur. usage: resid.py ERR.npy QUERY_IMG_DIR"""
import sys

import numpy as np

e = np.load(sys.argv[1])
P = np.load(sys.argv[2] + "/poses.npy")
dt, dr = e[:, 0], e[:, 1]
ret = np.isfinite(dt)
good = ret & (dt <= .25) & (dr <= 2)
wrong = ret & ((dt > 5) | (dr > 10))
mid = ret & ~good & ~wrong
r = np.linalg.norm(P[:, :2, 3], axis=1)
print(f"n={len(dt)} good {good.sum()} mid {mid.sum()} wrong {wrong.sum()} not-returned {(~ret).sum()}")
if wrong.any():
    print(f"wrong: pos_err/(2|xy|) median {np.median(dt[wrong]/(2*np.maximum(r[wrong],1e-6))):.2f}, rot>170deg {np.mean(dr[wrong] > 170):.0%}, rot>90deg {np.mean(dr[wrong] > 90):.0%}")
# where along the path (index buckets of 10 % of the sequence): fraction not good
b = np.array_split(np.arange(len(dt)), 10)
print("fraction NOT good per 10% of path:", [round(float(1 - good[i].mean()), 2) for i in b])
# the one with the largest share of failures: corner proximity? corners are the 4 turning points of the loop
cor = np.array([[-13, -9], [13, -9], [13, 9], [-13, 9]])
dc = np.linalg.norm(P[:, None, :2, 3] - cor[None], axis=2).min(1)
print(f"within 3 m of a corner: n={int((dc < 3).sum())}, not-good fraction {1 - good[dc < 3].mean():.2f} | elsewhere {1 - good[dc >= 3].mean():.2f}")
