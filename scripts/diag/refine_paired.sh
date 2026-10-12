#!/bin/bash
cd /mnt/a/SlamProject/results/urban
echo "== held-out ug1h: prior 5 m, no refine -> refine x2 (paired, per query)"
python3 /mnt/a/SlamProject/scripts/diag/paired.py heldout_prior_s5r20_err.npy refine2_ug1h_err.npy
echo "== tuned ug1s: prior 5 m, no refine -> refine x2"
python3 /mnt/a/SlamProject/scripts/diag/paired.py prior_s5r20_err.npy refine2_ug1s_err.npy
python3 /mnt/a/SlamProject/scripts/gate_curve.py refine2_ug1h_err.npy refine2_ug1s_err.npy
