#!/bin/bash
# queued behind the world queue (one heavy job at a time): (1) sensor-degradation evaluation on the original world, (2) AR head-height test on grid11
while ! grep -q ALLWORLDS_DONE /mnt/a/SlamProject/scripts/allworlds.log; do sleep 30; done
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_deg_all --out ../results/urban/deg_all.json --seed 0 2>&1 | grep -E "localized|Error" | tr -d ' \n'; echo
python3 /mnt/a/SlamProject/scripts/deg_analyze.py ../results/urban/deg_all_err.npy
echo 1 > /proc/sys/vm/drop_caches
echo DEG_DONE
bash /mnt/a/SlamProject/scripts/ar_test.sh grid11
echo AFTER_WORLDS_DONE
