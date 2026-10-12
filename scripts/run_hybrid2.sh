#!/bin/bash
# Hybrid on route 2: XFeat finds the pose (K=50), one render-at-estimate refine with DISK+LightGlue. Prior 5 m / r 20 m, and no prior.
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=xfeat M1LF_REFINE=1 M1LF_REFINE_MATCHER=disklg M1LF_K=50
run() { echo "--- $1"; python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_img --out ../results/urban/$1.json --seed 0 2>&1 | grep -E "\"localized|recall|median_t|latency_ms_p50|gate40|Error|error" | tr -d ' \n'; echo; }
PRIOR_SIGMA=5 M1LF_PRIOR_R=20 run hyb_xfeat_disk_prior
run hyb_xfeat_disk
echo 1 > /proc/sys/vm/drop_caches
echo HYB2_DONE
