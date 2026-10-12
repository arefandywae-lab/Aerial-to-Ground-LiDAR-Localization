#!/bin/bash
# Case 1 (AR/XR glasses): the same world and drone map, but the query camera is at HEAD height (1.7 m) with a slight downward pitch and a wider turn rate.
# (a) queries at 1.7 m against the ground-robot views (0.44 m) that all other results use: what breaks?  (b) against views rendered at 1.7 m.
# usage: ar_test.sh WORLD   (needs /root/data/w_WORLD with the drone map: map.npz, map_f2.npz, ud_img)
W=$1; source /opt/ros/jazzy/setup.bash; source /root/ws/install/setup.bash
R=/mnt/a/SlamProject; D=/root/data/w_$W; OUT=$R/results/worlds; A=${W}ar
python3 - <<PY
import re
s = open("/root/worlds/$W.sdf").read()
n = s.count("<pose>0.3 0 0.3 0 0 0</pose>")
s = s.replace("<pose>0.3 0 0.3 0 0 0</pose>", "<pose>0.3 0 1.55 0 0.1 0</pose>")  # camera 1.7 m above the ground (base is 0.15 m), pitched 0.1 rad down
open("/root/worlds/$A.sdf", "w").write(s); print("camera pose replaced:", n)
PY
cp /root/worlds/$W.json /root/worlds/$A.json
UG=$(python3 -c "import json;m=json.load(open('/root/worlds/$W.json'));print(';'.join('%.1f,%.1f'%tuple(p) for p in m['ground']))")
cd /root
[ -f $D/ar/metadata.yaml ] || { rm -rf $D/ar; bash $R/ros/run_urban_session.sh /root/worlds/$A.sdf ground "$UG" $D/ar 1.0; }
python3 $R/vps/dump_session.py $D/ar $D/ar_img 6 --frame robot --gt-topic /gt/ground --image /ground/camera/image_raw --info /ground/camera/camera_info 2>&1 | tail -1
python3 - <<PY
import os, shutil, numpy as np
src, dst = "$D/ar_img", "$D/ars_img"
shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst + "/images")
names = sorted(os.listdir(src + "/images"))[::2]; T = np.load(src + "/poses.npy")[::2]
for i, n in enumerate(names): os.symlink(f"{src}/images/{n}", f"{dst}/images/{i:05d}.png")
np.save(dst + "/poses.npy", T); shutil.copy(src + "/K.npy", dst + "/K.npy"); print("queries", len(names), "camera height median", float(np.median(T[:, 2, 3])))
PY
cd $R/vps; [ -f $D/views_h17.npy ] || python3 viewpoints.py $D/map.npz $D/views_h17.npy 6 8 1.7 | tail -n 1
echo 1 > /proc/sys/vm/drop_caches
export M1_MAP=$D/map_f2.npz M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1LF_RETR=megaloc M1LF_COARSE=0 M1LF_FP16=0 M1LF_MATCHER=disklg M1LF_K=20 PRIOR_SIGMA=5 M1LF_PRIOR_R=20
for V in views h17; do
  VF=$D/views.npy; [ $V = h17 ] && VF=$D/views_h17.npy
  M1_VIEWS=$VF python3 harness.py --method m1lf --map $D/ud_img --queries $D/ars_img --out $OUT/${W}_ar_$V.json --seed 0 2>&1 | grep -E "\"n\"|localized|recall|median_t|latency_ms_p50|gate40|Error" | tr -d ' \n' | sed "s/^/$W AR queries, views=$V prior: /"; echo
  echo 1 > /proc/sys/vm/drop_caches
done
echo AR_${W}_DONE
