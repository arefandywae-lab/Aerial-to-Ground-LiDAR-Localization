import sys, cv2, numpy as np, torch, traceback
sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1lf
from harness import load_session
M = m1lf.Method(); M.prepare("/root/data/s0_img")
q = load_session("/root/data/q1_img")
try:
    print(M.localize(cv2.imread(q["images"][10]), q["K"])[1])
except Exception:
    traceback.print_exc()
