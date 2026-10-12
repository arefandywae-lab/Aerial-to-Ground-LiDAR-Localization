#!/bin/bash
# C-decide: end-to-end urban test again after render fixes (class-aware colour fill, splat 0.12 m) on the SAME 205 queries as results/urban/m1_ug1s.json (9.8 % within (5 m,10 deg)).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_K=50 M1LF_TOPN=12 M1LF_COARSE=1 M1LF_FP16=0
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1s_img --out ../results/urban/m1_ug1s_v2.json --seed 0 2>&1 | grep -E "M1LF map|\"n\"|localized|recall|median|latency_ms_p50|gate40"
echo 1 > /proc/sys/vm/drop_caches
echo URBAN_M1_V2_DONE
