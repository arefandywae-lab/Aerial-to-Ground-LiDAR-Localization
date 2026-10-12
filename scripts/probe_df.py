import sys, os
sys.path.insert(0, "/mnt/a/SlamProject/vps")
import numpy as np, torch
import m1lf
M = m1lf.Method(); M.prepare("/root/data/ud0_img")
c = np.array([x[0].shape[0] for x in M.df]); print("render keypoints: min", c.min(), "median", int(np.median(c)), "max", c.max(), "share==2048:", float((c == 2048).mean()))
print(M.df[0][0].shape, M.df[0][1].shape)
