#!/bin/bash
# Independent ground route in the same city (C-heldout): street y=0 (never driven) + REVERSED direction on y=-50, x=50, x=-50 (different views of already-driven streets).
# Then evaluate with the SAME settings as 4g/4h (no re-tuning): prior 5 m / radius 20 m, and global (no prior).
cd /root
source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject
UG2="0,-50;50,-50;50,0;-50,0;-50,-50;0,-50"
[ -d /root/data/ug2 ] || bash $R/ros/run_urban_session.sh /root/worlds/urban.sdf ground "$UG2" /root/data/ug2 1.0
python3 $R/vps/dump_session.py /root/data/ug2 /root/data/ug2_img 6 --frame robot --gt-topic /gt/ground --image /ground/camera/image_raw --info /ground/camera/camera_info 2>&1 | tail -2
sync
python3 - <<'PY'
import os, shutil, numpy as np
src, dst = "/root/data/ug2_img", "/root/data/ug2s_img"
shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst + "/images")
names = sorted(os.listdir(src + "/images"))[::2]
T = np.load(src + "/poses.npy")[::2]
for i, n in enumerate(names):
    os.symlink(f"{src}/images/{n}", f"{dst}/images/{i:05d}.png")
np.save(dst + "/poses.npy", T); shutil.copy(src + "/K.npy", dst + "/K.npy")
G1 = np.load("/root/data/ug1_img/poses.npy")[:, :2, 3]
d = np.array([np.linalg.norm(G1 - p[:2, 3], axis=1).min() for p in T])
print("ug2s:", len(names), "queries | distance to the nearest ug1 pose: median %.1f m, share > 5 m: %.0f %%" % (np.median(d), 100 * (d > 5).mean()))
PY
echo 1 > /proc/sys/vm/drop_caches
cd $R/vps
export M1_MAP=/root/data/map_ud0_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=/root/data/views_ud0.npy M1LF_RETR=megaloc M1LF_COARSE=1 M1LF_FP16=0 M1LF_K=50 M1LF_TOPN=12
echo "--- route 2, prior 5 m / radius 20 m"
PRIOR_SIGMA=5 M1LF_PRIOR_R=20 python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_img --out ../results/urban/route2_prior_s5r20.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50" | tr -d ' \n'; echo
echo "--- route 2, global (no prior)"
python3 harness.py --method m1lf --map /root/data/ud0_img --queries /root/data/ug2s_img --out ../results/urban/route2_global.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50" | tr -d ' \n'; echo
echo 1 > /proc/sys/vm/drop_caches
echo ROUTE2_DONE
