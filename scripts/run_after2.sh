#!/bin/bash
# queued after run_after_hyb.sh: route-2 sequence with GLOBAL retrieval (no position prior), DISK+LightGlue, for the kidnapped-start MCL test.
while ! grep -q AFTER_DONE /mnt/a/SlamProject/scripts/after.log; do sleep 15; done
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50
NO_PRIOR=1 python3 /mnt/a/SlamProject/scripts/seq_collect.py /root/data/ug2_img /root/data/seq_ug2_disklg_global.npz 2>&1 | tail -n 2
echo 1 > /proc/sys/vm/drop_caches
echo AFTER2_DONE
