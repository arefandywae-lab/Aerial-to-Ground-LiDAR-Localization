#!/usr/bin/env python3
"""Drive the robot through waypoints using stamped GT (default /gt/model, transform whose child_frame_id == frame).
usage: drive_waypoints.py "x,y;x,y,s;..." [speed] [gt_topic=/gt/model] [cmd_topic=/cmd_vel] [frame=robot]   exits when the last waypoint is reached.
A waypoint written "x,y,s" additionally makes the robot spin one full turn in place on arrival (yaw sweep for held-out-viewpoint queries)."""
import math
import sys

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


class Driver(Node):
    def __init__(self, wps, v, gt_topic="/gt/model", cmd_topic="/cmd_vel", frame="robot"):
        super().__init__("drive_waypoints")
        self.wps, self.v, self.done = wps, v, False
        self.spun, self.last_yaw = None, None  # radians turned so far while spinning, previous yaw sample
        self.frame = frame
        self.pub = self.create_publisher(Twist, cmd_topic, 10)
        self.create_subscription(TFMessage, gt_topic, self.cb, 10)

    def cb(self, m):
        t = next((x.transform for x in m.transforms if x.child_frame_id == self.frame), None)
        if t is None:
            return
        x, y = t.translation.x, t.translation.y
        q = t.rotation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        if not self.wps:
            self.pub.publish(Twist())
            self.done = True
            return
        gx, gy, spin = self.wps[0]
        if self.spun is not None:  # spinning in place at the waypoint
            self.spun += abs(math.atan2(math.sin(yaw - self.last_yaw), math.cos(yaw - self.last_yaw)))
            self.last_yaw = yaw
            if self.spun >= 2 * math.pi:
                self.spun = None
                self.wps.pop(0)
                self.pub.publish(Twist())
                return
            c = Twist()
            c.angular.z = 0.6
            self.pub.publish(c)
            return
        if math.hypot(gx - x, gy - y) < 0.5:
            if spin:
                self.spun, self.last_yaw = 0.0, yaw
            else:
                self.wps.pop(0)
            return
        err = math.atan2(math.sin(math.atan2(gy - y, gx - x) - yaw), math.cos(math.atan2(gy - y, gx - x) - yaw))
        c = Twist()
        c.angular.z = max(-1.0, min(1.0, 1.5 * err))
        c.linear.x = self.v * max(0.0, math.cos(err)) ** 2  # slow down while turning
        self.pub.publish(c)


if __name__ == "__main__":
    wps = [(*map(float, p.split(",")[:2]), len(p.split(",")) > 2) for p in sys.argv[1].split(";")]
    rclpy.init()
    a = sys.argv
    d = Driver(wps, float(a[2]) if len(a) > 2 else 0.8, a[3] if len(a) > 3 else "/gt/model", a[4] if len(a) > 4 else "/cmd_vel", a[5] if len(a) > 5 else "robot")
    while rclpy.ok() and not d.done:
        rclpy.spin_once(d)
