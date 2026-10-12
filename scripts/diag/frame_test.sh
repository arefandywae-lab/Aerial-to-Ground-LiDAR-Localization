#!/bin/bash
# In which frame does VelocityControl interpret the drone's linear command? Yaw ~90 deg, then command +x for 4 s and look at the displacement.
cd /root; source /opt/ros/jazzy/setup.bash
R=/mnt/a/SlamProject; P="python3 $R/scripts/diag/gt_pos.py"
pkill -f "gz sim" 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; sleep 1
gz sim -s -r --headless-rendering /root/worlds/urban.sdf > /tmp/urban_gz.log 2>&1 &
sleep 22
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$R/ros/bridge_urban.yaml > /tmp/urban_br.log 2>&1 &
sleep 6
echo "start:               $($P /gt/drone drone)"
timeout 3.2 ros2 topic pub -r 20 /drone/cmd_vel geometry_msgs/msg/Twist '{angular: {z: 0.5}}' > /dev/null 2>&1
timeout 1 ros2 topic pub -r 20 /drone/cmd_vel geometry_msgs/msg/Twist '{}' > /dev/null 2>&1
echo "after yaw command:   $($P /gt/drone drone)"
timeout 4 ros2 topic pub -r 20 /drone/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 3.0}}' > /dev/null 2>&1
timeout 1 ros2 topic pub -r 20 /drone/cmd_vel geometry_msgs/msg/Twist '{}' > /dev/null 2>&1
echo "after +x 3 m/s 4 s:  $($P /gt/drone drone)"
pkill -f parameter_bridge; pkill -f "gz sim"
