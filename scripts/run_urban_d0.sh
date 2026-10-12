#!/bin/bash
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0.npz M1_ZFAR=120
python3 /mnt/a/SlamProject/scripts/urban_d0.py 2>&1 | grep -v -i warn
echo 1 > /proc/sys/vm/drop_caches
