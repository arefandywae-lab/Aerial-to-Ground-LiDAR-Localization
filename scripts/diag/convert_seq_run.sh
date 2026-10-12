#!/bin/bash
python3 /mnt/a/SlamProject/scripts/diag/convert_seq.py /root/data/seq_ug2.npz /root/data/seq_ug2_clean.npz
mv /root/data/seq_ug2_clean.npz /root/data/seq_ug2.npz
ps -eo pid,cmd | grep -E "seq_collect|harness" | grep -v grep | wc -l
