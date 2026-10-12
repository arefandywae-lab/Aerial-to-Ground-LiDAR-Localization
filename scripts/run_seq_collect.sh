#!/bin/bash
# V1 data: single-frame results and inlier correspondences for ALL 570 dumped frames of route 2 (ug2), prior 5 m / radius 20 m, settings of 4g.
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
python3 /mnt/a/SlamProject/scripts/seq_collect.py /root/data/ug2_img /root/data/seq_ug2.npz 2>&1 | grep -v -i warn | tail -3
echo 1 > /proc/sys/vm/drop_caches
echo SEQ_COLLECT_DONE
