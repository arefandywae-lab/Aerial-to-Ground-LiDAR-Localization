#!/bin/bash
cd /mnt/a/SlamProject
for N in 5 7 9 12; do
  python3 scripts/seq_consensus.py /root/data/seq_ug2.npz $N 0.01 0.1 2>&1 | grep -v -i warn
  echo
done
