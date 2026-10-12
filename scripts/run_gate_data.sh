#!/bin/bash
# Data for the confidence head: M1-LoFTR (fp32, coarse retrieval) with 4 yaws on a sparser map (M1L_STEP=12, ~3 s/query) so correctness is mixed; features logged by the harness.
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1LF_FP16=0 M1LF_COARSE=1 M1L_STEP=12 M1LF_YAWS=0,90,180,270
for q in q1v2 q2v2 q3v2; do
  [ -f ../results/v2/g12_${q}_feat.npy ] && { echo "skip $q (done)"; continue; }
  python3 harness.py --method m1lf --map /root/data/s0v2_img --queries /root/data/${q}_img --out ../results/v2/g12_${q}.json --seed 0 > /dev/null 2>&1
  echo "done $q"; echo 1 > /proc/sys/vm/drop_caches
done
echo 1 > /proc/sys/vm/drop_caches
echo GATE_DATA_DONE
