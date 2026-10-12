#!/bin/bash
# Gravity-aided refinement (simulated IMU gravity, noise 0.1 deg per axis) on the held-out urban queries, prior 5 m / radius 20 m.
# Baseline on the same queries: heldout_prior_s5r20 / pred_ug1h (35.6 % within (0.5 m,5 deg), median translation error 0.543 m).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
for sg in 0.1 0.5; do
  echo "--- gravity sigma $sg deg on ug1h"
  GRAV_SIGMA_DEG=$sg python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1h_img --out ../results/urban/grav${sg}_ug1h.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|median_r|latency_ms_p50" | tr -d ' \n'; echo
done
echo 1 > /proc/sys/vm/drop_caches
echo GRAV_DONE
