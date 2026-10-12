#!/usr/bin/env python3
"""LiDAR map (FAST-LIO camera_init frame) -> world-frame map with normals and optional colours.
usage: build_lidar_map.py SESSION_BAG ODOM_BAG MAP_NPY MAP_IMG_DIR OUT.npz

 - alignment camera_init -> world from GT (ros/eval_ate.align)
 - radius outlier removal, PCA normals
 - colour: each map point takes the mean colour of the mapping images that see it (z-buffer occlusion test).
   NOTE colours are projected with the GT camera poses, so map-quality experiments (exp 6) degrade geometry
   only; colour registration error is not part of that study."""
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ros"))
from eval_ate import align  # noqa: E402


def clean_and_normals(p, radius=float(os.environ.get("MAP_RADIUS", 0.3)), min_nb=4, k=12):
    tree = cKDTree(p)
    ok = np.array([len(x) for x in tree.query_ball_point(p, radius)]) >= min_nb
    p = p[ok]
    tree = cKDTree(p)
    _, nb = tree.query(p, k=k)
    q = p[nb] - p[nb].mean(1, keepdims=True)
    w, v = np.linalg.eigh(np.einsum("nki,nkj->nij", q, q))
    n = v[:, :, 0]  # smallest-eigenvalue direction
    return p, n


def calib_error(rot_deg, trans_m, seed=0):
    """fixed camera-extrinsic error (rotation about a random axis, translation in a random direction), applied in the camera frame to every image pose:
    the sensitivity test for a mis-calibrated camera-LiDAR/camera-odometry transform (real systems always have one)"""
    from scipy.spatial.transform import Rotation as Rot
    r = np.random.default_rng(seed)
    ax = r.normal(size=3); ax /= np.linalg.norm(ax)
    tr = r.normal(size=3); tr /= np.linalg.norm(tr)
    E = np.eye(4)
    E[:3, :3] = Rot.from_rotvec(ax * np.radians(rot_deg)).as_matrix()
    E[:3, 3] = tr * trans_m
    return E


def colorize(p, img_dir, tol=0.15):
    from harness import load_session
    s = load_session(img_dir)
    K = s["K"]
    E = calib_error(float(os.environ.get("COLOR_ROT_DEG", 0)), float(os.environ.get("COLOR_TRANS_M", 0)))
    jit = float(os.environ.get("COLOR_JITTER_M", 0))  # per-image position error (odometry-like), metres
    rj = np.random.default_rng(1)
    acc, cnt = np.zeros((len(p), 3)), np.zeros(len(p))
    for f, T in zip(s["images"], s["T"]):
        T = T @ E  # camera pose used for colouring = true pose composed with the (wrong) extrinsic
        if jit > 0:
            T = T.copy(); T[:3, 3] += rj.normal(0, jit, 3)
        img = cv2.imread(f)
        h, w = img.shape[:2]
        pc = (p - T[:3, 3]) @ T[:3, :3]  # world -> camera
        z = pc[:, 2]
        u = np.round(K[0, 0] * pc[:, 0] / np.maximum(z, 1e-6) + K[0, 2]).astype(int)
        v = np.round(K[1, 1] * pc[:, 1] / np.maximum(z, 1e-6) + K[1, 2]).astype(int)
        ok = (z > 0.3) & (u >= 1) & (u < w - 1) & (v >= 1) & (v < h - 1)
        idx = np.where(ok)[0]
        zb = np.full((h, w), np.inf)
        for du in (-1, 0, 1):  # 3x3 splat so 0.1 m voxels at range don't leave see-through holes
            for dv in (-1, 0, 1):
                np.minimum.at(zb, (v[idx] + dv, u[idx] + du), z[idx])
        vis = idx[z[idx] <= zb[v[idx], u[idx]] + tol]
        acc[vis] += img[v[vis], u[vis]]
        cnt[vis] += 1
    rgb = np.where(cnt[:, None] > 0, acc / np.maximum(cnt, 1)[:, None], 128).astype(np.uint8)
    return rgb, cnt


if __name__ == "__main__":
    sess, odom, mp, imgs, out = sys.argv[1:6]
    a = align(sess, odom, os.environ.get("GT_MODEL", "robot"), os.environ.get("GT_TOPIC", "/gt/model"))
    p = np.load(mp).astype(np.float64) @ a["R"].T + a["t"]
    p, n = clean_and_normals(p)
    rgb, cnt = colorize(p, imgs)
    np.savez(out, pts=p.astype(np.float32), normals=n.astype(np.float32), rgb=rgb)
    print(f"{out}: {len(p)} pts, extent {p.min(0).round(1)}..{p.max(0).round(1)}, seen-by-camera {(cnt > 0).mean():.0%}")
