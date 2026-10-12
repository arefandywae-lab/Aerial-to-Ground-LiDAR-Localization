# kill every simulation / pipeline process by pid (pkill -f from a script can match and kill its own shell)
for pat in run_all_worlds world_pipeline closed_loop drive_waypoints fly_waypoints "ros2 bag record" parameter_bridge "gz sim" harness.py ros2-daemon; do
  for p in $(ps -eo pid,cmd | grep -F "$pat" | grep -v grep | grep -v kill_all | awk '{print $1}'); do kill -9 $p 2>/dev/null; done
done
sleep 2
rm -rf /root/data/w_oldtown12/ug /root/data/w_oldtown12/ug_img /root/data/w_oldtown12/ugs_img
ps -eo pid,etime,cmd | grep -E "gz sim|ros2|rosbag|drive_wayp|world_pipeline|run_all|harness|fly_way" | grep -v grep | cut -c1-100
echo CLEAN; ls /root/data/w_oldtown12; free -m | head -2
