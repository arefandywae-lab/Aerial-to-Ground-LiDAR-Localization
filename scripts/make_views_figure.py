"""What do the drone and the ground robot see? Rows = worlds; columns = drone camera (looking down from the mapping flight) | ground robot camera | the coloured LiDAR map rendered at the robot's pose
(what the matcher compares the robot image with; grey = no drone image saw that surface, filled by the class-aware fill). usage: make_views_figure.py OUT.png"""
import os, sys
import cv2, numpy as np, torch
sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1lf
from m1 import shade

def lab(im, t):
    im = im.copy(); cv2.rectangle(im, (0, 0), (im.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(im, t, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1, cv2.LINE_AA); return im

def row(name, drone_dir, ground_dir, map_npz, gi, di):
    dfiles = sorted(os.listdir(f"{drone_dir}/images")); gfiles = sorted(os.listdir(f"{ground_dir}/images"))
    d = cv2.imread(f"{drone_dir}/images/{dfiles[di]}"); g = cv2.imread(f"{ground_dir}/images/{gfiles[gi]}")
    T = np.load(f"{ground_dir}/poses.npy")[gi]; K = np.load(f"{ground_dir}/K.npy")
    m = np.load(map_npz); Pg = torch.from_numpy(m["pts"]).float().cuda()
    r, _ = shade(m1lf.render_gpu(Pg, T, K), m["rgb"]); del Pg; torch.cuda.empty_cache()
    sz = (480, 360)
    ims = [cv2.resize(x, sz) for x in (d, g, r)]
    return np.hstack([lab(ims[0], f"{name}: DRONE camera (mapping flight)"), lab(ims[1], "GROUND ROBOT camera (query)"), lab(ims[2], "MAP rendered at the robot pose")])

rows = [row("original world", "/root/data/ud0_img", "/root/data/ug1_img", "/root/data/map_ud0_f2.npz", 240, 450),
        row("grid11", "/root/data/w_grid11/ud_img", "/root/data/w_grid11/ug_img", "/root/data/w_grid11/map_f2.npz", 300, 230),
        row("canyon15", "/root/data/w_canyon15/ud_img", "/root/data/w_canyon15/ug_img", "/root/data/w_canyon15/map_f2.npz", 300, 230)]
cv2.imwrite(sys.argv[1], np.vstack(rows)); print("saved", sys.argv[1], np.vstack(rows).shape)
