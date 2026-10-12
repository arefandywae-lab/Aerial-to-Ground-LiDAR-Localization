for d in /root/data/lio_ud0 /root/data/w_grid11/lio; do
  echo "== $d"; tail -n 3 $d/../lio_ud0.log 2>/dev/null | cut -c1-160
  ls $d | head -5
done
source /opt/ros/jazzy/setup.bash
for b in /root/data/ud0 /root/data/w_grid11/ud; do echo "== bag $b"; ros2 bag info $b 2>/dev/null | grep -E "Duration|/drone/lidar|/drone/imu|/gt/drone" ; done
for b in /root/data/lio_ud0/odom /root/data/w_grid11/lio/odom; do echo "== odom $b"; ros2 bag info $b 2>/dev/null | grep -E "Duration|Odometry|Messages"; done
