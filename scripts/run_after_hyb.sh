#!/bin/bash
# queued after the hybrid test (one heavy job at a time): DISK+LightGlue prior mode on the second session ug1s (gate needs >=2 sessions), then the per-frame sequence on route 2 for MCL.
while ! grep -q HYB2_DONE /mnt/a/SlamProject/scripts/hyb2.log; do sleep 15; done
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1s_img --out ../results/urban/disklg_ug1s_prior.json --seed 0 2>&1 | grep -E "\"localized|recall|median_t|latency_ms_p50|gate40" | tr -d ' \n'; echo
echo 1 > /proc/sys/vm/drop_caches
python3 /mnt/a/SlamProject/scripts/seq_collect.py /root/data/ug2_img /root/data/seq_ug2_disklg.npz 2>&1 | tail -n 2
echo 1 > /proc/sys/vm/drop_caches
echo AFTER_DONE
