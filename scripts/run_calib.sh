#!/bin/bash
# Colour-registration sensitivity: re-colour the drone map with a wrong camera extrinsic / odometry-like jitter, re-fill, evaluate with FROZEN settings
# (DISK+LightGlue K=20, prior 5 m / r 20 m) on route 2 (ug2s). Reference (exact poses): 93.0 % / 41.1 % / 0.566 m.
source /opt/ros/jazzy/setup.bash; source /root/ws/install/setup.bash
R=/mnt/a/SlamProject
cd $R/vps
for v in "rot0.5 0.5 0 0" "rot1 1 0 0" "rot2 2 0 0" "tr0.1 0 0.1 0" "jit0.1 0 0 0.1" "rot1jit0.1 1 0 0.1"; do
  set -- $v; tag=$1
  COLOR_ROT_DEG=$2 COLOR_TRANS_M=$3 COLOR_JITTER_M=$4 GT_MODEL=drone GT_TOPIC=/gt/drone MAP_RADIUS=0.6 python3 build_lidar_map.py /root/data/ud0 /root/data/lio_ud0/odom /root/data/lio_ud0/map.npy /root/data/ud0_img /root/data/map_ud0_$tag.npz 2>&1 | tail -n 1
  python3 $R/scripts/fill_colors2.py /root/data/map_ud0_$tag.npz /root/data/map_ud0_${tag}_f2.npz 1.0 16 0.8 2>&1 | tail -n 1
  echo 1 > /proc/sys/vm/drop_caches
  M1_MAP=/root/data/map_ud0_${tag}_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20 PRIOR_SIGMA=5 M1LF_PRIOR_R=20 \
    python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_img --out ../results/urban/calib_$tag.json --seed 0 2>&1 | grep -E "\"localized|recall|median_t|latency_ms_p50|gate40|Error" | tr -d ' \n' | sed "s/^/$tag: /"; echo
  echo 1 > /proc/sys/vm/drop_caches
done
echo CALIB_DONE
