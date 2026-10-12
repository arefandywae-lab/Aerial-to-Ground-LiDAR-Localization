"""Route 2 results stratified: novel street (> 5 m from every ug1 pose) vs streets already driven (but in the reverse direction). usage: route2_strata.py ERR.npy"""
import sys
import numpy as np
e = np.load(sys.argv[1]); T2 = np.load("/root/data/ug2s_img/poses.npy"); G1 = np.load("/root/data/ug1_img/poses.npy")[:, :2, 3]
d = np.array([np.linalg.norm(G1 - p[:2, 3], axis=1).min() for p in T2])
dt, dr, inl = e[:, 0], e[:, 1], e[:, 2]
for name, m in (("novel street (>5 m from ug1)", d > 5), ("already-driven streets, reverse direction", d <= 5)):
    for g in (0, 80):
        a = m & np.isfinite(dt) & (inl >= g)
        l = (dt[a] <= 5) & (dr[a] <= 10)
        print(f"{name:42s} n={m.sum():3d} gate>={g:3d}: returned {a.sum()/m.sum():5.1%} | of returned within (5 m,10deg) {l.mean():5.1%} | within (1 m,5deg) {np.mean((dt[a]<=1)&(dr[a]<=5)):5.1%} | gross-wrong {int((~l).sum()):3d} = {(~l).sum()/m.sum():5.1%} of the stratum")
