#!/bin/bash
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20 M1LF_PRIOR_R=20 M1LF_PRIOR_STRICT=1 M1LF_MAXD=8
python3 /mnt/a/SlamProject/scripts/replay_online.py ${1:-/root/data/ug2_img} /mnt/a/SlamProject/results/urban/replay_${2:-ug2}.npz 2 2>&1 | grep -E "^frame|REPLAY|Error|Traceback"
echo 1 > /proc/sys/vm/drop_caches
echo REPLAY_DONE
