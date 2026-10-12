"""Alignment sanity check for the urban data: real image next to a render of the LiDAR map at the SAME GT pose (drone and ground).
If the GT poses/extrinsics/frames are consistent with the map, structure must line up. usage: overlay_urban.py OUT.png"""
import sys

import cv2
import numpy as np

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1
from harness import load_session

d = np.load("/root/data/map_ud0.npz")
P, rgb = d["pts"].astype(np.float64), d["rgb"]
rows = []
for name, idxs in (("ud0_img", (60, 220, 380)), ("ug1_img", (80, 300, 560))):
    s = load_session(f"/root/data/{name}")
    for i in idxs:
        real = cv2.imread(s["images"][i])
        img, ids = m1.render(P, rgb, s["T"][i], s["K"])
        for im, t in ((real, f"{name[:3]} {i} real"), (img, f"{name[:3]} {i} map render")):
            cv2.putText(im, t, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
        rows.append(np.hstack([real, img]))
cv2.imwrite(sys.argv[1], np.vstack(rows))
print("wrote", sys.argv[1])
