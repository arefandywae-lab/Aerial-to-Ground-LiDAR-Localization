#!/bin/bash
cd /mnt/a/SlamProject/results/urban
python3 - <<'PY'
import numpy as np
for n in ("heldout_prior_s5r20", "prov_ray1_ug1h", "prov_ray0_ug1h"):
    e = np.load(n + "_err.npy"); a = np.isfinite(e[:, 0]) & (e[:, 2] >= 80)
    l = (e[a, 0] <= 5) & (e[a, 1] <= 10)
    print(f"{n:22s} gate>=80: accepted {a.mean():5.1%} | within (5m,10deg) {l.mean():5.1%} | gross-wrong {np.sum(~l)/len(e):5.1%} of all | within 1m {np.mean(e[a,0]<=1):5.1%} | within 0.5m {np.mean(e[a,0]<=.5):5.1%} | median {np.median(e[a,0][l]):.3f} m")
PY
