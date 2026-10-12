#!/bin/bash
# Re-run the baseline (voxel-centre provenance, prior 5 m / radius 20 m) on ug1h while SAVING the estimated poses, to analyse the error vectors (bias field vs noise).
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug1h_img --out ../results/urban/pred_ug1h.json --seed 0 2>&1 | grep -E "recall@0.5|median_t" | tr -d ' \n'; echo
echo 1 > /proc/sys/vm/drop_caches
echo PRED_DONE
