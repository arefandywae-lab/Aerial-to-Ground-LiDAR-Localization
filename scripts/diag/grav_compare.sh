#!/bin/bash
cd /mnt/a/SlamProject/results/urban
for f in heldout_prior_s5r20 grav0.1_ug1h grav0.5_ug1h; do python3 /mnt/a/SlamProject/scripts/gate_curve.py ${f}_err.npy | grep -E "==|   40 |   80 |  150 "; done
python3 - <<'PY'
import numpy as np
for n in ("heldout_prior_s5r20", "grav0.1_ug1h", "grav0.5_ug1h"):
    e = np.load(n + "_err.npy"); a = np.isfinite(e[:, 0]) & (e[:, 2] >= 80) & (e[:, 0] < 5)
    print(f"{n:22s} accepted n={a.sum():3d}: translation err median {np.median(e[a,0]):.3f} m (p25 {np.percentile(e[a,0],25):.3f}, p75 {np.percentile(e[a,0],75):.3f}), rotation median {np.median(e[a,1]):.2f} deg; within 0.25 m {np.mean(e[a,0]<=.25):.1%}, 0.5 m {np.mean(e[a,0]<=.5):.1%}, 1 m {np.mean(e[a,0]<=1):.1%}")
PY
