#!/bin/bash
# global (no prior) sequences with 8 per-view PnP hypotheses per frame, DISK+LightGlue, for the multi-hypothesis MCL (routes 2 and 3)
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50 M1LF_HYP=8 NO_PRIOR=1
for r in 2 3; do python3 /mnt/a/SlamProject/scripts/seq_collect.py /root/data/ug${r}_img /root/data/seq_ug${r}_hyp_global.npz 2>&1 | tail -n 1; echo 1 > /proc/sys/vm/drop_caches; done
echo HYPC_DONE
