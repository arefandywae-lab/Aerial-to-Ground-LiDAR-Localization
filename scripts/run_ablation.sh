#!/bin/bash
# Ablation of m1lf speed-ups vs the m1l baseline (results/m1l_q1_s0.json). Seed 0, same q1 queries. Order: fastest first.
# tag: F=fp16, C=coarse retrieval. c0f0 = GPU z-buffer renderer only (isolates the renderer change from fp16/retrieval).
cd /mnt/a/SlamProject/vps
for cfg in "1 1 f1c1" "0 1 f0c1" "1 0 f1c0" "0 0 f0c0"; do
  set -- $cfg
  echo "=== fp16=$1 coarse=$2 ($3) ==="
  M1LF_FP16=$1 M1LF_COARSE=$2 python3 harness.py --method m1lf --map /root/data/s0_img --queries /root/data/q1_img \
    --out ../results/m1lf_$3_s0.json --seed 0 2>&1 | grep -E 'M1LF map|localized|recall@0.25|recall@5|latency_ms_p50|latency_ms_p95|vram|gate40_prec'
done
echo ALLDONE
