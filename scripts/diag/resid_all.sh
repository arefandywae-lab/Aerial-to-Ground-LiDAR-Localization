#!/bin/bash
for r in yaw0_q2v2:q2v2 yaw4_q2v2:q2v2 yaw4_q1v2:q1v2; do n=${r%%:*}; q=${r##*:}; echo "== $n"; python3 /mnt/a/SlamProject/scripts/diag/resid.py /mnt/a/SlamProject/results/v2/${n}_err.npy /root/data/${q}_img; done
