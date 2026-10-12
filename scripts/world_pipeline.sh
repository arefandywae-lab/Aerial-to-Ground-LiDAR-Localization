#!/bin/bash
# End-to-end generalisation run on one generated world, FROZEN settings (nothing is tuned per world).
# usage: world_pipeline.sh NAME   (needs /root/worlds/NAME.sdf and NAME.json from worlds/gen_city.py)
# drone mapping flight -> FAST-LIO -> coloured map (camera poses from the sim) -> filled map -> ground-level views -> ground drive -> evaluation:
# DISK+LightGlue, MegaLoc shortlist K=20, (a) prior 5 m / r 20 m, (b) global (no prior)
W=$1
source /opt/ros/jazzy/setup.bash; source /root/ws/install/setup.bash
R=/mnt/a/SlamProject; D=/root/data/w_$W; OUT=$R/results/worlds
mkdir -p $D $OUT
UD=$(python3 -c "import json;m=json.load(open('/root/worlds/$W.json'));print(';'.join('%g,%g,%g'%tuple(p) for p in m['drone']))")
UG=$(python3 -c "import json;m=json.load(open('/root/worlds/$W.json'));print(';'.join('%.1f,%.1f'%tuple(p) for p in m['ground']))")
cd /root
[ -f $D/ud/metadata.yaml ] || { rm -rf $D/ud; bash $R/ros/run_urban_session.sh /root/worlds/$W.sdf drone "$UD" $D/ud 4; }
python3 $R/vps/dump_session.py $D/ud $D/ud_img 5 --frame drone --gt-topic /gt/drone --image /drone/camera/image_raw --info /drone/camera/camera_info 2>&1 | tail -1
echo 1 > /proc/sys/vm/drop_caches
if [ ! -f $D/views.npy ]; then  # map steps are skipped when a previous run already produced them
export LIO_CFG=$R/ros/fastlio_drone.yaml LIDAR_TOPIC=/drone/lidar/points IMU_TOPIC=/drone/imu
bash $R/ros/run_lio.sh $D/ud $D/lio > $D/lio.log 2>&1
cd $R/ros
python3 eval_ate.py $D/ud $D/lio/odom drone /gt/drone | tee $OUT/${W}_ate.txt
python3 build_map.py $D/lio/odom $D/lio/map.npy 0.25
GT_MODEL=drone GT_TOPIC=/gt/drone MAP_RADIUS=0.6 python3 $R/vps/build_lidar_map.py $D/ud $D/lio/odom $D/lio/map.npy $D/ud_img $D/map.npz | tee $OUT/${W}_map.txt
python3 $R/scripts/fill_colors2.py $D/map.npz $D/map_f2.npz 1.0 16 0.8 | tee -a $OUT/${W}_map.txt
cd $R/vps; python3 viewpoints.py $D/map.npz $D/views.npy 6 8 0.44 | tee -a $OUT/${W}_map.txt
fi
echo 1 > /proc/sys/vm/drop_caches
cd /root
[ -f $D/ug/metadata.yaml ] || { rm -rf $D/ug; bash $R/ros/run_urban_session.sh /root/worlds/$W.sdf ground "$UG" $D/ug 1.0; }
python3 $R/vps/dump_session.py $D/ug $D/ug_img 6 --frame robot --gt-topic /gt/ground --image /ground/camera/image_raw --info /ground/camera/camera_info 2>&1 | tail -1
python3 - <<PY
import os, shutil, numpy as np
src, dst = "$D/ug_img", "$D/ugs_img"
shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst + "/images")
names = sorted(os.listdir(src + "/images"))[::2]
T = np.load(src + "/poses.npy")[::2]
for i, n in enumerate(names): os.symlink(f"{src}/images/{n}", f"{dst}/images/{i:05d}.png")
np.save(dst + "/poses.npy", T); shutil.copy(src + "/K.npy", dst + "/K.npy"); print("queries", len(names))
PY
python3 $R/scripts/world_check.py $W 2>&1 | tee $OUT/${W}_check.txt
echo 1 > /proc/sys/vm/drop_caches
cd $R/vps
export M1_MAP=$D/map_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_VIEWS=$D/views.npy M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20
PRIOR_SIGMA=5 M1LF_PRIOR_R=20 python3 harness.py --method m1lf --map $D/ud_img --queries $D/ugs_img --out $OUT/${W}_prior.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50|gate40|Error" | tr -d ' \n' | sed "s/^/$W prior: /"; echo
echo 1 > /proc/sys/vm/drop_caches
python3 harness.py --method m1lf --map $D/ud_img --queries $D/ugs_img --out $OUT/${W}_global.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50|gate40|Error" | tr -d ' \n' | sed "s/^/$W global: /"; echo
echo 1 > /proc/sys/vm/drop_caches
echo WORLD_${W}_DONE
