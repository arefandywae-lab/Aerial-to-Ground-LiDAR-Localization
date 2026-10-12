"""Print the world position of one frame from a stamped GT TFMessage topic. usage: gt_pos.py TOPIC FRAME [timeout_s=6]"""
import math
import sys
import time

import rclpy
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


class N(Node):
    def __init__(self, topic, frame):
        super().__init__("gt_pos")
        self.frame, self.out = frame, None
        self.create_subscription(TFMessage, topic, self.cb, 10)

    def cb(self, m):
        for x in m.transforms:
            if x.child_frame_id == self.frame and self.out is None:
                t = x.transform.translation
                q = x.transform.rotation
                yaw = math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))
                self.out = (round(t.x, 2), round(t.y, 2), round(t.z, 2), f"yaw={yaw:.0f}deg")


rclpy.init()
n = N(sys.argv[1], sys.argv[2])
end = time.time() + float(sys.argv[3] if len(sys.argv) > 3 else 6)
while rclpy.ok() and n.out is None and time.time() < end:
    rclpy.spin_once(n, timeout_sec=0.2)
print(n.out)
