#!/usr/bin/env python3
"""Fly the floating drone (VelocityControl, gravity off) through 3D waypoints with a P controller on stamped GT.
VelocityControl interprets the LINEAR command in the BODY frame (verified: yawed 95 deg, +x command moved the drone along world +y), so the drone yaws towards
the travel direction (camera then looks forward along every lane: facade faces on both sides of a street are seen on opposite lanes). Set YAW_FOLLOW=0 to hold yaw 0.
usage: fly_waypoints.py "x,y,z;x,y,z;..." [speed=4] [gt_topic=/gt/drone] [cmd_topic=/drone/cmd_vel] [frame=drone]   exits at the last waypoint."""
import math
import os
import sys

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from tf2_msgs.msg import TFMessage


YAW_FOLLOW = int(os.environ.get("YAW_FOLLOW", 1))


class Flyer(Node):
    def __init__(self, wps, v, gt_topic, cmd_topic, frame):
        super().__init__("fly_waypoints")
        self.wps, self.v, self.frame, self.done = wps, v, frame, False
        self.pub = self.create_publisher(Twist, cmd_topic, 10)
        self.create_subscription(TFMessage, gt_topic, self.cb, 10)

    def cb(self, m):
        tf = next((x.transform for x in m.transforms if x.child_frame_id == self.frame), None)
        if tf is None:
            return
        t, q = tf.translation, tf.rotation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        if not self.wps:
            self.pub.publish(Twist())
            self.done = True
            return
        gx, gy, gz = self.wps[0]
        dx, dy, dz = gx - t.x, gy - t.y, gz - t.z
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        if d < 0.7:
            self.wps.pop(0)
            return
        s = min(self.v, 0.5 * d + 0.3) / d  # slow down near the waypoint
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
        self.pub.publish(c)


if __name__ == "__main__":
    a = sys.argv
    wps = [tuple(map(float, p.split(","))) for p in a[1].split(";")]
    rclpy.init()
    f = Flyer(wps, float(a[2]) if len(a) > 2 else 4.0, a[3] if len(a) > 3 else "/gt/drone", a[4] if len(a) > 4 else "/drone/cmd_vel",
              a[5] if len(a) > 5 else "drone")
    while rclpy.ok() and not f.done:
        rclpy.spin_once(f)
