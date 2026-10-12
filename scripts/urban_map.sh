#!/bin/bash
# Series B step 2 (CPU): FAST-LIO2 on the drone flight, ATE vs GT, world-frame coloured LiDAR map.
cd /root
source /opt/ros/jazzy/setup.bash; source /root/ws/install/setup.bash
R=/mnt/a/SlamProject
export LIO_CFG=$R/ros/fastlio_drone.yaml LIDAR_TOPIC=/drone/lidar/points IMU_TOPIC=/drone/imu
bash $R/ros/run_lio.sh /root/data/ud0 /root/data/lio_ud0 > /root/data/lio_ud0.log 2>&1
cat /root/data/lio_ud0/resort.log
cd $R/ros
python3 eval_ate.py /root/data/ud0 /root/data/lio_ud0/odom drone /gt/drone | tee $R/results/ate_ud0.txt
python3 build_map.py /root/data/lio_ud0/odom /root/data/lio_ud0/map.npy 0.25
GT_MODEL=drone GT_TOPIC=/gt/drone MAP_RADIUS=0.6 python3 $R/vps/build_lidar_map.py /root/data/ud0 /root/data/lio_ud0/odom /root/data/lio_ud0/map.npy /root/data/ud0_img /root/data/map_ud0.npz
sync; echo 1 > /proc/sys/vm/drop_caches  # return page cache (vmmem otherwise holds it and Windows can run out of commit)
echo URBAN_MAP_DONE
