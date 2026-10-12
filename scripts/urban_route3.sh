#!/bin/bash
# HELD-OUT route 3 (settings frozen before running): new loop with y=0 EAST, y=50 WEST, x=-50 south..., start (0,0). Evaluate DISK+LightGlue (K=50), prior 5 m / r 20 m, then the per-frame sequence for MCL (SXY 1.5, INJECT 0.1 fixed in advance).
cd /root
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
UG3="0,0;50,0;50,50;-50,50;-50,0;0,0;0,-50;50,-50"
[ -d /root/data/ug3 ] || bash $R/ros/run_urban_session.sh /root/worlds/urban.sdf ground "$UG3" /root/data/ug3 1.0
python3 $R/vps/dump_session.py /root/data/ug3 /root/data/ug3_img 6 --frame robot --gt-topic /gt/ground --image /ground/camera/image_raw --info /ground/camera/camera_info 2>&1 | tail -2
sync
python3 - <<'PY'
import os, shutil, numpy as np
src, dst = "/root/data/ug3_img", "/root/data/ug3s_img"
shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst + "/images")
names = sorted(os.listdir(src + "/images"))[::2]
T = np.load(src + "/poses.npy")[::2]
for i, n in enumerate(names):
    os.symlink(f"{src}/images/{n}", f"{dst}/images/{i:05d}.png")
np.save(dst + "/poses.npy", T); shutil.copy(src + "/K.npy", dst + "/K.npy")
P = np.concatenate([np.load(f"/root/data/{s}_img/poses.npy")[:, :2, 3] for s in ("ug1", "ug2")])
d = np.array([np.linalg.norm(P - p[:2, 3], axis=1).min() for p in T])
print("ug3s:", len(names), "queries | distance to the nearest ug1/ug2 pose: median %.1f m, share > 5 m: %.0f %%" % (np.median(d), 100 * (d > 5).mean()))
PY
echo 1 > /proc/sys/vm/drop_caches
cd $R/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=50
echo "--- route 3, DISK+LightGlue, prior 5 m / radius 20 m"
PRIOR_SIGMA=5 M1LF_PRIOR_R=20 python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug3s_img --out ../results/urban/route3_disklg_prior.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50|gate40" | tr -d ' \n'; echo
echo 1 > /proc/sys/vm/drop_caches
echo "--- route 3, DISK+LightGlue, global"
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug3s_img --out ../results/urban/route3_disklg_global.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50|gate40" | tr -d ' \n'; echo
echo 1 > /proc/sys/vm/drop_caches
PRIOR_SIGMA=5 M1LF_PRIOR_R=20 python3 $R/scripts/seq_collect.py /root/data/ug3_img /root/data/seq_ug3_disklg.npz 2>&1 | tail -n 1
echo 1 > /proc/sys/vm/drop_caches
echo ROUTE3_DONE
