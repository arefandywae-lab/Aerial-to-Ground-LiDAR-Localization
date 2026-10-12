"""Ground-level virtual viewpoints from the LiDAR map itself (no GT trajectory, no building list): a grid of positions on known ground,
kept only where no obstacle points lie within CLEAR m, each with several yaws at a fixed camera height. Writes (N,4,4) camera-to-world poses in
OpenCV optical convention (x right, y down, z forward) for `M1_VIEWS` (vps/m1lf.py).
usage: viewpoints.py MAP.npz OUT.npy [spacing=6] [yaws=8] [cam_height=0.44]   (also writes OUT_layout.png: kept positions over the obstacle footprint)"""
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

CLEAR = 1.2  # m, min distance from obstacle points (the robot is ~0.6 m wide)
GROUND_Z = 0.3  # points below this are "ground"; points between GROUND_Z and OBST_Z are obstacles seen at robot height
OBST_Z = 2.0


def sample(pts, spacing=6.0, n_yaw=8, h=0.44):
    ground = pts[pts[:, 2] < GROUND_Z]
    obst = pts[(pts[:, 2] >= GROUND_Z) & (pts[:, 2] < OBST_Z)]
    tg, to = cKDTree(ground[:, :2]), cKDTree(obst[:, :2])
    lo, hi = pts[:, :2].min(0), pts[:, :2].max(0)
    gx, gy = np.meshgrid(np.arange(lo[0], hi[0], spacing), np.arange(lo[1], hi[1], spacing))
    cand = np.c_[gx.ravel(), gy.ravel()]
    d_g, _ = tg.query(cand)
    d_o, _ = to.query(cand)
    keep = (d_g < 2.0) & (d_o > CLEAR)  # known ground underneath, nothing at robot height nearby
    xy = cand[keep]
    poses = []
    for x, y in xy:
        for k in range(n_yaw):
            yaw = 2 * np.pi * k / n_yaw
            f = np.array([np.cos(yaw), np.sin(yaw), 0.0])
            dn = np.array([0.0, 0.0, -1.0])
            r = np.cross(dn, f)  # right = down x forward (right-handed OpenCV frame)
            T = np.eye(4)
            T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = r, dn, f, [x, y, h]
            poses.append(T)
    return np.array(poses), xy, obst


if __name__ == "__main__":
    d = np.load(sys.argv[1])
    sp = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    ny = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    h = float(sys.argv[5]) if len(sys.argv) > 5 else 0.44
    poses, xy, obst = sample(d["pts"], sp, ny, h)
    np.save(sys.argv[2], poses)
    print(f"{len(xy)} positions x {ny} yaws = {len(poses)} views (spacing {sp} m, camera height {h} m)")
    lo = d["pts"][:, :2].min(0)
    s = 4.0
    img = np.zeros((int((d["pts"][:, 1].max() - lo[1]) * s) + 4, int((d["pts"][:, 0].max() - lo[0]) * s) + 4, 3), np.uint8)
    for x, y in obst[::3, :2]:
        img[int((y - lo[1]) * s), int((x - lo[0]) * s)] = (90, 90, 90)
    for x, y in xy:
        cv2.circle(img, (int((x - lo[0]) * s), int((y - lo[1]) * s)), 2, (0, 220, 0), -1)
    cv2.imwrite(sys.argv[2].replace(".npy", "_layout.png"), img[::-1])
