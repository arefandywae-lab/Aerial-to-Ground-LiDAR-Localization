#!/bin/bash
# Full pipeline with XFeat as matcher on the independent route 2 (ug2s): MegaLoc shortlist K -> XFeat on every shortlisted view -> PnP.
cd /mnt/a/SlamProject/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=xfeat
for K in 20 50; do
  echo "--- XFeat, no prior, K=$K"
  M1LF_K=$K python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_img --out ../results/urban/xfeat_ug2s_k$K.json --seed 0 2>&1 | grep -E "\"localized|recall|median_t|latency_ms_p50|gate40|within" | tr -d ' \n'; echo
done
echo 1 > /proc/sys/vm/drop_caches
echo XFEAT_DONE
