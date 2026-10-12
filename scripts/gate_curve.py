"""Accepted-pose quality as a function of the inlier gate, for one run (CPU). usage: gate_curve.py ERR.npy [ERR.npy ...]  (columns: dt, dr, inliers)"""
import sys
import numpy as np
for f in sys.argv[1:]:
    e = np.load(f); dt, dr, inl = e[:, 0], e[:, 1], e[:, 2]; n = len(e)
    print(f"== {f.split('/')[-1]}  (n={n})")
    print(f"{'gate':>6s} {'accepted':>9s} {'usable(0.5m,5deg)':>18s} {'<=1m,5deg':>10s} {'<=5m,10deg':>11s} {'wrong>5m/10deg':>15s}")
    for g in (12, 20, 40, 80, 150, 300):
        a = np.isfinite(dt) & (inl >= g)
        if not a.any():
            continue
        u = (dt[a] <= .5) & (dr[a] <= 5); m = (dt[a] <= 1) & (dr[a] <= 5); l = (dt[a] <= 5) & (dr[a] <= 10)
        print(f"{g:6d} {a.mean():9.1%} {u.mean():18.1%} {m.mean():10.1%} {l.mean():11.1%} {int((~l).sum()):6d} ({(~l).sum()/n:.1%} of all queries)")
