"""Summarise results/v2: per method and query set, mean +- std over seeds (sample std) for the main metrics, plus per-query failure analysis.
usage: summarize_v2.py [results/v2]   (CPU only)"""
import glob
import json
import os
import re
import sys

import numpy as np

D = sys.argv[1] if len(sys.argv) > 1 else "/mnt/a/SlamProject/results/v2"
Q = {"q1v2": "/root/data/q1v2_img", "q2v2": "/root/data/q2v2_img"}
S = np.load("/root/data/s0v2_img/poses.npy")
KEYS = ["localized", "recall@0.25m,2.0deg", "recall@0.5m,5.0deg", "recall@5.0m,10.0deg", "median_t_m", "median_r_deg", "latency_ms_p50", "gate40_precision"]
runs = {}
for f in sorted(glob.glob(f"{D}/*_s[0-9].json")):
    m = re.match(r".*/(m\w+?)_(q\dv2)_s(\d)\.json", f)
    if m:
        runs.setdefault((m[1], m[2]), []).append(json.load(open(f)))
print(f"{'method':6s} {'queries':6s} {'seeds':>5s} " + " ".join(f"{k.replace('recall@','R@').replace(',2.0deg','').replace(',5.0deg','').replace(',10.0deg','')[:14]:>14s}" for k in KEYS))
for (meth, q), rs in sorted(runs.items(), key=lambda x: (x[0][1], x[0][0])):
    cells = []
    for k in KEYS:
        v = np.array([r[k] for r in rs if r.get(k) is not None], float)
        if not len(v):
            cells.append(f"{'-':>14s}")
        elif "latency" in k:
            cells.append(f"{v.mean():10.0f} ms  ")
        elif "median" in k:
            cells.append(f"{v.mean():8.3f}+-{v.std(ddof=1) if len(v) > 1 else 0:.3f}")
        else:
            cells.append(f"{100*v.mean():6.1f}+-{100*(v.std(ddof=1) if len(v) > 1 else 0):.1f}%")
    print(f"{meth:6s} {q:6s} {len(rs):>5d} " + " ".join(f"{c:>14s}" for c in cells))
print("\nper-query analysis (seed 0):")
for (meth, q), rs in sorted(runs.items(), key=lambda x: (x[0][1], x[0][0])):
    f = f"{D}/{meth}_{q}_s0_err.npy"
    if not os.path.exists(f) or not os.path.exists(Q[q] + "/poses.npy"):
        continue
    e = np.load(f)
    P = np.load(Q[q] + "/poses.npy")
    dt, dr = e[:, 0], e[:, 1]
    ret = np.isfinite(dt)
    wrong = ret & ((dt > 5) | (dr > 10))
    near = np.array([np.linalg.norm(S[:, :3, 3] - p[:3, 3], axis=1).min() for p in P])
    ang = np.array([np.degrees(np.arccos(np.clip((np.trace(S[np.linalg.norm(S[:, :3, 3] - p[:3, 3], axis=1).argmin(), :3, :3].T @ p[:3, :3]) - 1) / 2, -1, 1))) for p in P])
    r = np.linalg.norm(P[:, :2, 3], axis=1)
    mir = (dt[wrong] / (2 * np.maximum(r[wrong], 1e-6)))
    print(f"{meth:5s} {q}: n={len(dt)} returned {ret.sum()} wrong {wrong.sum()} | query->map: dist med {np.median(near):.2f} m, yaw diff med {np.median(ang):.0f} deg"
          + (f" | wrong poses pos_err/(2|xy|) median {np.median(mir):.2f}, rot>170deg {np.mean(dr[wrong] > 170):.0%}" if wrong.any() else ""))
