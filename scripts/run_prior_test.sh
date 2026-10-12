#!/bin/bash
# Prior-aided ("tracking") mode on the urban test queries: candidate views limited to a radius around a noisy position prior (GT + N(0, sigma^2) xy).
# Compare with the no-prior run results/urban/m1_ug1s_v2.json (50.2 % within (5 m,10 deg), 23.4 % within (0.5 m,5 deg), 2.34 s).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0
run() {  # tag sigma radius K topn
  echo "--- $1 (prior sigma $2 m, radius $3 m, K=$4, top-N=$5)"
  PRIOR_SIGMA=$2 M1LF_PRIOR_R=$3 M1LF_K=$4 M1LF_TOPN=$5 python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1s_img --out ../results/urban/prior_$1.json --seed 0 2>&1 \
    | grep -E "\"localized|recall|median_t|latency_ms_p50|gate40" | tr -d ' \n'; echo
}
run s5r20 5 20 50 12
run s10r35 10 35 50 12
echo 1 > /proc/sys/vm/drop_caches
echo PRIOR_DONE
