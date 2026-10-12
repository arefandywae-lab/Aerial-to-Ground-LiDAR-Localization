#!/bin/bash
# A28 render-and-refine on the urban queries, prior sigma 5 m / radius 20 m, 0 vs 2 iterations. Baselines: tuned set prior_s5r20 (31.7 % within (0.5 m,5 deg), 81.5 % within (5 m,10 deg)); held-out heldout_prior_s5r20 (35.6 %, 80.5 %).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
for q in ug1h ug1s; do
  echo "--- refine x2 on $q"
  M1LF_REFINE=2 python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/${q}_img --out ../results/urban/refine2_${q}.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50" | tr -d ' \n'; echo
done
echo 1 > /proc/sys/vm/drop_caches
echo REFINE_DONE
