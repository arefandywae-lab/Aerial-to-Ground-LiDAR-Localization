#!/bin/bash
# V1 step 2 over several odometry-noise levels and window sizes (CPU only).
cd /mnt/a/SlamProject
for cfg in "5 0 0" "5 0.01 0.1" "5 0.03 0.3" "9 0.01 0.1" "5 0.01 0.1 2"; do
  python3 scripts/seq_solve.py /root/data/seq_ug2.npz $cfg 2>&1 | grep -v -i warn
  echo
done
