"""M1: map-as-images with provenance. LiDAR map (coloured points) is rendered from virtual viewpoints; every pixel keeps
the index of the map point that produced it. SIFT on the render -> descriptor + metric 3D from provenance. Retrieval and
PnP are M0's (same matcher on camera and render images, no cross-modal training). Only the map source differs.
Virtual viewpoints = mapping poses; extra yaw/lateral offsets are the knob if recall is low (exp 6 varies the map itself)."""
import os

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

import m0
from harness import load_session

LIDAR_MAP = os.environ.get("M1_MAP", "/root/data/map_s0.npz")
SPLAT_M = float(os.environ.get("M1_SPLAT", 0.03))  # world radius of a map point in the render; sets hole filling vs. blur (0.03 for a 0.1 m map, ~0.12 for a 0.25 m voxel map)
FILL_PX = 12  # max hole-fill distance; sparse LiDAR leaves ~10 px gaps on near surfaces
SKY = 218  # the sim sky is flat light grey
ZFAR = float(os.environ.get("M1_ZFAR", 25))  # far clip of the render in metres: 25 suits the 30 x 20 m room; the urban map needs ~120
STEP = int(os.environ.get("M1_STEP", 1))  # use every STEP-th mapping pose as a virtual viewpoint


def render(P, rgb, T_c2w, K, size=(640, 480)):
    """-> (bgr image, int32 point-index map, -1 = empty). Painter's order: far first, near overwrites."""
    w, h = size
    pc = (P - T_c2w[:3, 3]) @ T_c2w[:3, :3]
    z = pc[:, 2]
    vis = np.where((z > 0.5) & (z < ZFAR))[0]
    vis = vis[np.argsort(-z[vis])]
    u = (K[0, 0] * pc[vis, 0] / z[vis] + K[0, 2]).round().astype(int)
    v = (K[1, 1] * pc[vis, 1] / z[vis] + K[1, 2]).round().astype(int)
    r = np.clip((K[0, 0] * SPLAT_M / z[vis]).round().astype(int), 0, 4)
    img, ids = np.zeros((h, w, 3), np.uint8), np.full((h, w), -1, np.int32)
    for rr in range(5):  # draw far (small r) first, near (large r) last so near overwrites far
        sel = r == rr
        for du in range(-rr, rr + 1):
            for dv in range(-rr, rr + 1):
                uu, vv = u[sel] + du, v[sel] + dv
                ok = (uu >= 0) & (uu < w) & (vv >= 0) & (vv < h)
                img[vv[ok], uu[ok]] = rgb[vis[sel][ok]]
                ids[vv[ok], uu[ok]] = vis[sel][ok]
    return shade(ids, rgb)


def shade(ids, rgb):
    """hole-fill ids from the nearest rendered pixel (provenance follows: filled pixels point at that neighbour's map point),
    then colour from the map and blur -> (bgr image, ids)"""
    dist, (iy, ix) = distance_transform_edt(ids < 0, return_indices=True)
    fill = (ids < 0) & (dist <= FILL_PX)
    ids[fill] = ids[iy[fill], ix[fill]]
    img = np.where((ids >= 0)[..., None], rgb[np.maximum(ids, 0)], SKY).astype(np.uint8)
    return cv2.GaussianBlur(img, (0, 0), 1.0), ids


class Method(m0.Method):
    def _keyframes(self, map_dir):
        s = load_session(map_dir)
        self.K = s["K"]
        d = np.load(LIDAR_MAP)
        P, rgb = d["pts"].astype(np.float64), d["rgb"]  # rgb is BGR (colorize samples cv2 images)
        f = m0.sift()
        desc, pts = [], []
        for T in s["T"][::STEP]:
            img, ids = render(P, rgb, T, self.K)
            kp, de = f.detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
            if de is None:
                continue
            pid = np.array([ids[int(round(k.pt[1])), int(round(k.pt[0]))] for k in kp])
            ok = pid >= 0
            if ok.sum() >= 12:
                desc.append(de[ok])
                pts.append(P[pid[ok]])
        return desc, pts
