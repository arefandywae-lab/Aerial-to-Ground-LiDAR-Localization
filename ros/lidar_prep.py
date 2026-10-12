#!/usr/bin/env python3
"""Gazebo gpu_lidar cloud -> Velodyne-style cloud (x,y,z,intensity,ring,time) for FAST-LIO2.

Gazebo scans are instantaneous (no motion during a sweep), so `time` is only a tiny monotonic
ramp (1 us per column) to keep FAST-LIO's per-point sort happy without introducing fake deskew.
Drops non-finite points. Input is organised: height = rings, width = columns.
"""
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField

OUT = np.dtype([("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("intensity", "<f4"),
                ("ring", "<u2"), ("time", "<f4")])  # itemsize 22 (packed)


class Prep(Node):
    def __init__(self):
        super().__init__("lidar_prep")
        self.pub = self.create_publisher(PointCloud2, "/velodyne_points", 5)
        self.declare_parameter("in_topic", "/lidar/points")
        self.create_subscription(PointCloud2, self.get_parameter("in_topic").value, self.cb, 5)

    def cb(self, m):
        f = {x.name: x.offset for x in m.fields}
        dt = np.dtype({"names": ["x", "y", "z"], "formats": ["<f4"] * 3,
                       "offsets": [f["x"], f["y"], f["z"]], "itemsize": m.point_step})
        a = np.frombuffer(m.data, dtype=dt, count=m.width * m.height)
        ring, col = np.divmod(np.arange(a.size), m.width)
        ok = np.isfinite(a["x"]) & np.isfinite(a["y"]) & np.isfinite(a["z"])
        o = np.empty(int(ok.sum()), OUT)
        o["x"], o["y"], o["z"] = a["x"][ok], a["y"][ok], a["z"][ok]
        o["intensity"] = 0.0
        o["ring"] = ring[ok]
        o["time"] = col[ok] * 1e-6  # seconds (fastlio_sim.yaml: timestamp_unit 0 = seconds)
        out = PointCloud2(header=m.header, height=1, width=o.size, is_dense=True,
                          is_bigendian=False, point_step=OUT.itemsize,
                          row_step=OUT.itemsize * o.size, data=o.tobytes())
        out.fields = [PointField(name=n, offset=OUT.fields[n][1], datatype=t, count=1)
                      for n, t in [("x", 7), ("y", 7), ("z", 7), ("intensity", 7), ("ring", 4), ("time", 7)]]
        self.pub.publish(out)


if __name__ == "__main__":
    rclpy.init()
    rclpy.spin(Prep())
