#!/bin/bash
# rebuild ATE + map + views of one world from its existing flight data with the trimmed alignment. usage: rebuild_map.sh NAME
W=$1; source /opt/ros/jazzy/setup.bash; source /root/ws/install/setup.bash
R=/mnt/a/SlamProject; D=/root/data/w_$W; OUT=$R/results/worlds
cd $R/ros
python3 eval_ate.py $D/ud $D/lio/odom drone /gt/drone | tee $OUT/${W}_ate.txt
GT_MODEL=drone GT_TOPIC=/gt/drone MAP_RADIUS=0.6 python3 $R/vps/build_lidar_map.py $D/ud $D/lio/odom $D/lio/map.npy $D/ud_img $D/map.npz | tee $OUT/${W}_map.txt
python3 $R/scripts/fill_colors2.py $D/map.npz $D/map_f2.npz 1.0 16 0.8 | tee -a $OUT/${W}_map.txt
cd $R/vps; python3 viewpoints.py $D/map.npz $D/views.npy 6 8 0.44 | tee -a $OUT/${W}_map.txt
echo 1 > /proc/sys/vm/drop_caches
ls $D/ug_img >/dev/null 2>&1 && python3 $R/scripts/world_check.py $W
