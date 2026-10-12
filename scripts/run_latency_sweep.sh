#!/bin/bash
# Accuracy/latency frontier with MegaLoc retrieval on the room (yaw4, step 6). Baseline mega_* = K50, coarse, top-12 full (2.3 s). Profile: coarse 1.09 s + full 1.17 s dominate.
#  k20t6    : shortlist 20, coarse stage, 6 full-res                         (~1.0 s expected)
#  direct8  : top-8 by MegaLoc straight to full-res, no coarse stage          (~0.8 s expected)
#  k20t6h   : k20t6 with fp16 LoFTR (earlier fp16+coarse lost accuracy; re-check with retrieval)
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1L_STEP=6 M1LF_YAWS=0,90,180,270 M1LF_RETR=megaloc
run() {  # tag fp16 coarse K topn
  for q in q2v2 q3v2 q1v2; do
    M1LF_FP16=$2 M1LF_COARSE=$3 M1LF_K=$4 M1LF_TOPN=$5 python3 harness.py --method m1lf --map /root/data/s0v2_img --queries /root/data/${q}_img --out ../results/v2/lat_$1_${q}.json --seed 0 > /root/lat_$1_${q}.log 2>&1
    echo "$1 $q: $(grep -E 'localized|recall@0.25|recall@5.0|latency_ms_p50' ../results/v2/lat_$1_${q}.json | tr -d ' \n')"
    echo 1 > /proc/sys/vm/drop_caches
  done
}
run k20t6 0 1 20 6
run direct8 0 0 8 8
run k20t6h 1 1 20 6
echo SWEEP_DONE
