"""Summarise a session's GT camera trajectory as a coarse waypoint list (Douglas-Peucker on xy) + stats. usage: trajectory.py SESSION_IMG_DIR [tol_m]"""
import sys

import cv2
import numpy as np

T = np.load(f"{sys.argv[1]}/poses.npy")
tol = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
xy = T[:, :2, 3].astype(np.float32)
poly = cv2.approxPolyDP(xy.reshape(-1, 1, 2), tol, False).reshape(-1, 2)
path = np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()
print(f"{sys.argv[1]}: {len(T)} poses, path {path:.1f} m, x {xy[:,0].min():.1f}..{xy[:,0].max():.1f} y {xy[:,1].min():.1f}..{xy[:,1].max():.1f}, "
      f"cam z {T[:,2,3].mean():.2f}")
print("waypoints:", ";".join(f"{x:.1f},{y:.1f}" for x, y in poly))
