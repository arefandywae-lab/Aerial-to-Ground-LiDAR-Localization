import rclpy, json, math
from rclpy.node import Node
from tf2_msgs.msg import TFMessage
rclpy.init(); n = Node("pos")
res = {}
def cb(m):
    for t in m.transforms:
        if t.child_frame_id == "robot": res["p"] = (t.transform.translation.x, t.transform.translation.y)
n.create_subscription(TFMessage, "/gt/ground", cb, 10)
for _ in range(60):
    rclpy.spin_once(n, timeout_sec=0.2)
    if "p" in res: break
g = json.load(open("/root/worlds/oldtown12.json"))["ground"]
p = res.get("p"); print("robot at", p)
if p:
    d = [math.hypot(p[0]-w[0], p[1]-w[1]) for w in g]; k = min(range(len(g)), key=lambda i: d[i]); print("nearest waypoint", k, "of", len(g), "dist", round(d[k], 1))
