"""Pointing error shown to an AR user: an anchor placed R metres ahead lands off by about R*tan(rotation error) + translation error. usage: ar_metrics.py RESULT_PREFIX [...]"""
import sys, numpy as np
for pre in sys.argv[1:]:
    E = np.load(pre + "_err.npy"); ok = np.isfinite(E[:, 0]); dt, dr = E[ok, 0], np.radians(E[ok, 1])
    line = f"{pre}: {ok.mean():.0%} with a pose |"
    for R in (10, 20, 50):
        e = np.hypot(dt, R * np.tan(np.minimum(dr, 1.5)))
        line += f" anchor@{R}m: median {np.median(e):.2f} m, within 0.5 m {np.mean(e <= .5):.0%}, within 2 m {np.mean(e <= 2):.0%} |"
    print(line)
