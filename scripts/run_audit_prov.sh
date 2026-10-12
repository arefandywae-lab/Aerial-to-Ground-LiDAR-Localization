#!/bin/bash
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4
python3 /mnt/a/SlamProject/scripts/audit_provenance.py /root/data/ug1h_img 40 2>&1 | grep -v -i warn
echo 1 > /proc/sys/vm/drop_caches
