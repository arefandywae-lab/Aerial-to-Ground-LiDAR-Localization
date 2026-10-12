#!/bin/bash
# Re-run M0, M1, M1-LoFTR after audit fixes, 3 seeds each.
set -e
cd /mnt/a/SlamProject/vps
for s in 0 1 2; do
  for mth in m0 m1 m1l; do
    out=../results/${mth}_q1_s${s}.json
    echo "=== $mth seed=$s ==="
    python3 harness.py --method $mth --map /root/data/s0_img --queries /root/data/q1_img --out $out --seed $s 2>&1 \
      | grep -E 'localized|recall@0.25|recall@5|method|latency_ms_p50|latency_ms_p95|gate20|gate40|vram_peak|M0 map|M1L map' || true
  done
done
