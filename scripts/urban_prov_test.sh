#!/bin/bash
# Ray-consistent provenance (+ drop hole-filled correspondences) on the held-out urban queries, prior 5 m / radius 20 m, settings of 4g.
# Baseline on the same queries: pred_ug1h (35.6 % within (0.5 m,5 deg), median 0.543 m; gate>=80: 59 % accepted, 98.3 % within (5 m,10 deg), 52.9 % within 0.5 m).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
for cfg in "ray 1" "ray 0"; do
  set -- $cfg
  echo "--- M1_PROV=$1 M1_DROP_FILLED=$2 on ug1h"
  M1_PROV=$1 M1_DROP_FILLED=$2 python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1h_img --out ../results/urban/prov_$1$2_ug1h.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|median_r|latency_ms_p50" | tr -d ' \n'; echo
done
echo 1 > /proc/sys/vm/drop_caches
echo PROV_DONE
