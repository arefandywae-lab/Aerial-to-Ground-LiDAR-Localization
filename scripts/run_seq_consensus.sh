#!/bin/bash
cd /mnt/a/SlamProject
for cfg in "7 0 0" "7 0.01 0.1" "7 0.03 0.3" "5 0.01 0.1"; do
  python3 scripts/seq_consensus.py /root/data/seq_ug2.npz $cfg 2>&1 | grep -v -i warn
  echo
done
