"""One-off patch (run from repo root) for the urban series: drone yaw-follow, parametrised FAST-LIO topics/frames, ATE for any vehicle."""
import io


def rw(path, fn):
    s = io.open(path, encoding="utf-8").read()
    s2 = fn(s)
    assert s2 != s, f"no change in {path}"
    io.open(path, "w", encoding="utf-8", newline="\n").write(s2)


def fly(s):
    s = s.replace("Yaw is held at 0 (no angular command) so body and world axes coincide: this avoids depending on the frame in which VelocityControl\ninterprets the linear command. Camera/LiDAR therefore look along +x; lanes flown in -x see backwards, which is fine for mapping.",
                  "VelocityControl interprets the LINEAR command in the BODY frame (verified: yawed 95 deg, +x command moved the drone along world +y), so the drone yaws towards\nthe travel direction (camera then looks forward along every lane: facade faces on both sides of a street are seen on opposite lanes). Set YAW_FOLLOW=0 to hold yaw 0.")
    s = s.replace("import math\nimport sys\n", "import math\nimport os\nimport sys\n")
    s = s.replace("        t = next((x.transform.translation for x in m.transforms if x.child_frame_id == self.frame), None)\n        if t is None:\n            return\n",
                  "        tf = next((x.transform for x in m.transforms if x.child_frame_id == self.frame), None)\n        if tf is None:\n            return\n        t, q = tf.translation, tf.rotation\n        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))\n")
    s = s.replace("        s = min(self.v, 0.5 * d + 0.3) / d  # slow down near the waypoint\n        c = Twist()\n        c.linear.x, c.linear.y, c.linear.z = dx * s, dy * s, dz * s\n        self.pub.publish(c)",
                  """        s = min(self.v, 0.5 * d + 0.3) / d  # slow down near the waypoint
        vx, vy, vz = dx * s, dy * s, dz * s
        c = Twist()
        if YAW_FOLLOW and math.hypot(dx, dy) > 3.0:
            err = math.atan2(math.sin(math.atan2(dy, dx) - yaw), math.cos(math.atan2(dy, dx) - yaw))
            c.angular.z = max(-0.6, min(0.6, 1.2 * err))
            k = max(0.0, math.cos(err)) ** 2  # turn first, translate when aligned (vertical motion unaffected)
            vx, vy = vx * k, vy * k
        c.linear.x = math.cos(yaw) * vx + math.sin(yaw) * vy  # world -> body frame
        c.linear.y = -math.sin(yaw) * vx + math.cos(yaw) * vy
        c.linear.z = vz
        self.pub.publish(c)""")
    s = s.replace("class Flyer(Node):", 'YAW_FOLLOW = int(os.environ.get("YAW_FOLLOW", 1))\n\n\nclass Flyer(Node):')
    return s


def lidar_prep(s):
    s = s.replace('        self.create_subscription(PointCloud2, "/lidar/points", self.cb, 5)',
                  '        self.declare_parameter("in_topic", "/lidar/points")\n        self.create_subscription(PointCloud2, self.get_parameter("in_topic").value, self.cb, 5)')
    return s


def run_lio(s):
    s = s.replace('R=$(dirname "$(readlink -f "$0")")',
                  'R=$(dirname "$(readlink -f "$0")")\n# env: LIO_CFG (default fastlio_sim.yaml), LIDAR_TOPIC (/lidar/points), IMU_TOPIC (/imu)\nCFG=${LIO_CFG:-$R/fastlio_sim.yaml}; LT=${LIDAR_TOPIC:-/lidar/points}; IT=${IMU_TOPIC:-/imu}')
    s = s.replace('python3 $R/resort_bag.py "$1" "$2/sorted"', 'python3 $R/resort_bag.py "$1" "$2/sorted" /clock $IT $LT')
    s = s.replace("python3 $R/lidar_prep.py --ros-args -p use_sim_time:=true", "python3 $R/lidar_prep.py --ros-args -p use_sim_time:=true -p in_topic:=$LT")
    s = s.replace("--params-file $R/fastlio_sim.yaml", "--params-file $CFG")
    s = s.replace("--topics /clock /lidar/points /imu", "--topics /clock $LT $IT")
    return s


def ate(s):
    s = s.replace('def align(sess_bag, odom_bag):', 'def align(sess_bag, odom_bag, model="robot", topic="/gt/model"):')
    s = s.replace("    gt_t, pos, q = gt_track(sess_bag)\n", "    gt_t, pos, q = gt_track(sess_bag, model, topic)\n")
    s = s.replace('sensor_in_base(sess_bag, "robot/base/imu")', 'sensor_in_base(sess_bag, f"{model}/base/imu", topic)')
    s = s.replace("    a_ = align(sys.argv[1], sys.argv[2])", "    a_ = align(sys.argv[1], sys.argv[2], *(sys.argv[3:5]))  # optional: model frame, GT topic")
    return s


def lidar_map(s):
    s = s.replace("    a = align(sess, odom)", "    a = align(sess, odom, os.environ.get(\"GT_MODEL\", \"robot\"), os.environ.get(\"GT_TOPIC\", \"/gt/model\"))")
    s = s.replace("def clean_and_normals(p, radius=0.3, min_nb=4, k=12):", "def clean_and_normals(p, radius=float(os.environ.get(\"MAP_RADIUS\", 0.3)), min_nb=4, k=12):")
    return s


rw("ros/fly_waypoints.py", fly)
rw("ros/lidar_prep.py", lidar_prep)
rw("ros/run_lio.sh", run_lio)
rw("ros/eval_ate.py", ate)
rw("vps/build_lidar_map.py", lidar_map)
print("patched")
