#!/bin/bash
# kidnapped-start success rate of the frozen multi-hypothesis MCL (SXY 1.0, EPS 0.5, HMIN 60, 5000 particles) over many start places, routes 2 and 3
cd /mnt/a/SlamProject
for r in 2 3; do
  N=$([ $r = 2 ] && echo 569 || echo 821)
  for st in $(seq 0 80 $((N-200))); do
    for seed in 3 4; do
      out=$(START=$st SEED=$seed UNI=${UNI:-0} KIDNAP=1 MULTIHYP=1 SXY=1.0 HMIN=60 python3 scripts/mcl_test.py /root/data/seq_ug${r}_hyp_global.npz 0.01 0.1 0.5 5000 2>&1 | grep -E "KIDNAPPED|MCL estimate" | cut -c1-230 | tr '\n' ' ')
      echo "route $r start $st seed $seed: $out"
    done
  done
done
echo MHSTARTU_DONE
