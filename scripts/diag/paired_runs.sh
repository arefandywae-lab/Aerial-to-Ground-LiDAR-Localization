#!/bin/bash
cd /mnt/a/SlamProject/results/v2
for q in q1v2 q2v2 q3v2; do
  echo "== $q: brute-force (yaw4) vs MegaLoc shortlist"
  python3 /mnt/a/SlamProject/scripts/diag/paired.py yaw4_${q}_err.npy mega_${q}_err.npy
done
