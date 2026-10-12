#!/bin/bash
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0.npz M1_ZFAR=120 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_K=50 M1LF_TOPN=12 M1LF_COARSE=1 M1LF_FP16=0
python3 /mnt/a/SlamProject/scripts/urban_diag.py 2>&1 | grep -v -i warn
echo 1 > /proc/sys/vm/drop_caches
