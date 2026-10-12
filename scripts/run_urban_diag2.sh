#!/bin/bash
# Same diagnosis as run_urban_diag.sh (retrieval D2, oracle D1, colour D3) with the fixed render (class-aware fill, splat 0.12 m).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_K=50 M1LF_TOPN=12 M1LF_COARSE=1 M1LF_FP16=0
python3 /mnt/a/SlamProject/scripts/urban_diag.py 2>&1 | grep -v -i warn
echo 1 > /proc/sys/vm/drop_caches
