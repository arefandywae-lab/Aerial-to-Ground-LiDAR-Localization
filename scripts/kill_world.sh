# stop only the running world pipeline (and its children); the queue script then continues / finishes by itself
for p in $(ps -eo pid,cmd | grep -F "world_pipeline.sh $1" | grep -v grep | awk '{print $1}'); do pkill -9 -P $p 2>/dev/null; kill -9 $p 2>/dev/null; done
for pat in build_lidar_map fill_colors2 viewpoints.py harness.py drive_waypoints "ros2 bag record" parameter_bridge "gz sim"; do for p in $(ps -eo pid,cmd | grep -F "$pat" | grep -v grep | grep -v kill_world | awk '{print $1}'); do kill -9 $p 2>/dev/null; done; done
sleep 2; ps -eo pid,etime,cmd | grep -E "world_pipeline|run_all|harness|gz sim" | grep -v grep | cut -c1-100
