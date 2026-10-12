#!/bin/bash
cd /mnt/a/SlamProject/results/urban
echo "== held-out ug1h: voxel-centre provenance -> plane-corrected (paired)"
python3 /mnt/a/SlamProject/scripts/diag/paired.py heldout_prior_s5r20_err.npy plane_ug1h_err.npy
python3 /mnt/a/SlamProject/scripts/gate_curve.py plane_ug1h_err.npy | head -8
python3 - <<'PY'
import numpy as np
for n in ("heldout_prior_s5r20", "plane_ug1h"):
    e = np.load(n + "_err.npy"); a = np.isfinite(e[:, 0]) & (e[:, 2] >= 80)
    print(n, "accepted(>=80 inliers) n=%d | translation err median %.3f m, p25 %.3f, p75 %.3f | rotation err median %.2f deg" % (a.sum(), np.median(e[a, 0]), np.percentile(e[a, 0], 25), np.percentile(e[a, 0], 75), np.median(e[a, 1])))
PY
