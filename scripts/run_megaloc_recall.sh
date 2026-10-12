#!/bin/bash
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1L_STEP=6 M1LF_YAWS=0,90,180,270
python3 /mnt/a/SlamProject/scripts/megaloc_recall.py 2>&1 | grep -v Warn
echo 1 > /proc/sys/vm/drop_caches
