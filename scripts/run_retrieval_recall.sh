#!/bin/bash
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_s0v2.npz M1L_STEP=6 M1LF_YAWS=0,90,180,270
python3 /mnt/a/SlamProject/scripts/retrieval_recall.py 1x1,2x2,3x4 2>&1 | grep -v Warn
