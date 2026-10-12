#!/usr/bin/env python3
"""CLOSED-LOOP test: the ground robot drives through waypoints using ONLY its own estimate (camera localizer + MCL + noisy odometry), live in Gazebo.
 - localizer: DISK+LightGlue render-and-match (vps/m1lf.py) against the drone's coloured LiDAR map; its position prior is the filter's own estimate (not GT)
 - filter: vps/mcl.py (planar MCL), odometry = GT increments with 1 % scale noise + heading noise (stand-in for wheel/IMU odometry), delayed update (the filter state at the image time is
   restored, updated with the pose, then the odometry since is replayed)
 - controller: heads for the next waypoint using the ESTIMATE; stops while the filter spread is above STOP_SPREAD (position uncertain)
 - GT is used only for the odometry simulation and for scoring: cross-track error to the planned path, collisions (map points at robot height within 0.35 m), success
usage: closed_loop.py "x,y;x,y;..." OUT.npz [speed=1.0]   env: as vps/m1lf.py (M1_MAP, M1_VIEWS, M1LF_*), MAP_IMG (drone session for prepare), STOP_SPREAD, TIMEOUT_X, SEED"""
import math
import os
import sys
import threading
import time

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.parameter import Parameter
from scipy.spatial import cKDTree
from sensor_msgs.msg import CameraInfo, Image
from tf2_msgs.msg import TFMessage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vps"))
import m1lf  # noqa: E402
from mcl import MCL, wrap  # noqa: E402

CAM_FWD = 0.3  # camera is 0.3 m ahead of the base origin (worlds/gen_world.py ROBOT)


class Loop(Node):
    def __init__(self, wps, out, v):
        super().__init__("closed_loop", parameter_overrides=[Parameter("use_sim_time", Parameter.Type.BOOL, True)])
        self.wps, self.path, self.out, self.v, self.i = [tuple(w) for w in wps], np.array(wps, float), out, v, 0
        self.stop_spread = float(os.environ.get("STOP_SPREAD", 15.0))  # lost: stop
        self.slow_spread = float(os.environ.get("SLOW_SPREAD", 2.0))  # uncertain: crawl on odometry at 40 % speed (stopping would deadlock where no pose passes the gates)
        self.rng = np.random.default_rng(int(os.environ.get("SEED", 0)))
        self.lock = threading.Lock()
        self.gt, self.gt_prev, self.K, self.img, self.img_t = None, None, None, None, None
        self.mcl, self.odo_log, self.snap, self.new_obs = None, [], None, None
        self.rows, self.t0, self.done, self.status = [], None, False, "running"
        self.stopped_ticks = 0
        self.n_loc, self.n_obs, self.n_rej, self.last_log = 0, 0, 0, 0.0
        M = None
        if not os.environ.get("STUB"):  # STUB=1: no localizer (tests the ROS plumbing and the controller quickly; the robot then runs on odometry alone)
            M = m1lf.Method()
            M.prepare(os.environ.get("MAP_IMG", "/root/data/ud0_img"))
        self.M = M
        d = np.load(os.environ["M1_MAP"])
        pts = d["pts"]
        ob = pts[(pts[:, 2] > 0.6) & (pts[:, 2] < 2.0)]  # above ground noise
        self.obst = cKDTree(ob[:, :2])
        self.pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.create_subscription(TFMessage, "/gt/ground", self.on_gt, 10)
        self.create_subscription(Image, "/ground/camera/image_raw", self.on_img, 1)
        self.create_subscription(CameraInfo, "/ground/camera/camera_info", self.on_info, 1)
        self.create_timer(0.1, self.tick)
        threading.Thread(target=self.worker, daemon=True).start()
        self.get_logger().info("ready")

    def on_info(self, m):
        self.K = np.array(m.k, float).reshape(3, 3)

    def on_gt(self, m):
        t = next((x.transform for x in m.transforms if x.child_frame_id == "robot"), None)
        if t is None:
            return
        q = t.rotation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        self.gt = np.array([t.translation.x, t.translation.y, yaw])

    def on_img(self, m):
        a = np.frombuffer(m.data, np.uint8).reshape(m.height, m.width, -1)
        a = cv2.cvtColor(a, cv2.COLOR_RGB2BGR) if m.encoding == "rgb8" else a.copy()
        with self.lock:
            if self.mcl is not None and self.img is None:  # worker is idle: take this frame and remember the filter state at its time
                self.img, self.snap = a, (self.mcl.snapshot(), len(self.odo_log))

    def worker(self):
        while rclpy.ok() and not self.done:
            with self.lock:
                img, snap, K = self.img, self.snap, self.K
            if img is None or K is None:
                time.sleep(0.02)
                continue
            prior = None
            with self.lock:
                if self.mcl.spread() < 10.0:
                    prior = self.mcl.mean()[:2] + 0.0
            try:
                T, info = self.M.localize(img, K, prior_xy=prior) if self.M is not None else (None, {})
            except Exception:
                import traceback
                traceback.print_exc()
                sys.stdout.flush()
                T, info = None, {}
            self.n_loc += 1
            with self.lock:
                if T is not None and info.get("inliers", 0) >= 12:
                    h = math.atan2(T[1, 2], T[0, 2])
                    base = T[:2, 3] - CAM_FWD * np.array([math.cos(h), math.sin(h)])
                    self.new_obs = (snap, np.array([base[0], base[1], h]), info["inliers"])
                    self.n_obs += 1
                self.img = None

    def tick(self):
        if self.gt is None or self.K is None:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        gt = self.gt.copy()
        if self.mcl is None:  # operator-supplied approximate start: +-5 m, +-10 deg
            self.mcl = MCL(gt[:2], gt[2], seed=int(os.environ.get("SEED", 0)))
            self.gt_prev, self.t0 = gt, now
            return
        # simulated odometry from GT increments (+ scale and heading noise)
        c, s = math.cos(self.gt_prev[2]), math.sin(self.gt_prev[2])
        d = gt[:2] - self.gt_prev[:2]
        rel = np.array([c * d[0] + s * d[1], -s * d[0] + c * d[1]])
        dist = float(np.hypot(*rel))
        rel_m = rel * (1 + self.rng.normal(0, 0.01)) + self.rng.normal(0, 0.002, 2)
        dpsi_m = float(wrap(gt[2] - self.gt_prev[2])) + math.radians(self.rng.normal(0, 0.1 * dist + 0.02))
        self.gt_prev = gt
        with self.lock:
            self.mcl.predict(rel_m, dpsi_m)
            self.odo_log.append((rel_m, dpsi_m))
            if self.new_obs is not None:  # delayed update
                (psnap, idx), obs, inl = self.new_obs
                self.new_obs = None
                self.mcl.restore(psnap)
                self.n_rej += 0 if self.mcl.update(obs, inl) else 1
                for r, dp in self.odo_log[idx:]:
                    self.mcl.predict(r, dp)
            est, spread = self.mcl.mean(), self.mcl.spread()
        # control with the estimate
        cmd = Twist()
        if self.i >= len(self.wps):
            self.pub.publish(cmd)
            self.status, self.done = "reached", True
            return
        gx, gy = self.wps[self.i]
        if math.hypot(gx - est[0], gy - est[1]) < 2.0:
            self.i += 1
            return
        if spread > self.stop_spread:
            self.stopped_ticks += 1
        else:
            err = wrap(math.atan2(gy - est[1], gx - est[0]) - est[2])
            cmd.angular.z = max(-1.0, min(1.0, 1.5 * err))
            cmd.linear.x = self.v * (0.4 if spread > self.slow_spread else 1.0) * max(0.0, math.cos(err)) ** 2
        self.pub.publish(cmd)
        if now - self.last_log > 10:
            self.last_log = now
            print(f"t={now - self.t0:5.0f}s gt=({gt[0]:6.1f},{gt[1]:6.1f}) est=({est[0]:6.1f},{est[1]:6.1f}) spread={spread:5.2f} wp {self.i}/{len(self.wps)} localizations={self.n_loc} obs={self.n_obs} rejected={self.n_rej}", flush=True)
        # scoring
        dmin = float(self.obst.query(gt[:2])[0])
        seg = self.path
        xt = min(self._dist_seg(gt[:2], seg[k], seg[k + 1]) for k in range(len(seg) - 1))
        self.rows.append((now - self.t0, *gt, *est, spread, float(spread > self.stop_spread), dmin, xt, self.i))
        if now - self.t0 > float(os.environ.get("TIMEOUT_X", 3.0)) * self.path_len() / self.v:
            self.status, self.done = "timeout", True

    def path_len(self):
        return float(np.sum(np.linalg.norm(np.diff(self.path, axis=0), axis=1)))

    @staticmethod
    def _dist_seg(p, a, b):
        ab = b - a
        t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1)
        return float(np.linalg.norm(p - (a + t * ab)))

    def save(self):
        r = np.array(self.rows)
        np.savez(self.out, rows=r, status=self.status, path=self.path)
        if len(r):
            err = np.linalg.norm(r[:, 4:6] - r[:, 1:3], axis=1)
            print(f"RESULT status={self.status} time={r[-1, 0]:.0f}s waypoints {self.i}/{len(self.wps)} | est error median {np.median(err):.2f} m p95 {np.percentile(err, 95):.2f} m max {err.max():.1f} m"
                  f" | cross-track median {np.median(r[:, 10]):.2f} m max {r[:, 10].max():.2f} m | collision ticks (<0.35 m) {int((r[:, 9] < 0.35).sum())}"
                  f" | stopped (uncertain) {100 * r[:, 8].mean():.0f} % of time", flush=True)


def main():
    wps = [tuple(map(float, p.split(","))) for p in sys.argv[1].split(";")]
    rclpy.init()
    n = Loop(wps, sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
    try:
        while rclpy.ok() and not n.done:
            rclpy.spin_once(n, timeout_sec=0.05)
    finally:
        n.pub.publish(Twist())
        n.save()


if __name__ == "__main__":
    main()
