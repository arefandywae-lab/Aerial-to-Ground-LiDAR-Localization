"""Where do the ~850 ms of one localization go? Times each stage on 40 route-2 queries (prior mode), CUDA-synchronised.
env as run_disklg.sh. usage: profile_latency.py"""
import sys, time
import cv2, numpy as np, torch
sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1l, m1lf
from harness import load_session
q = load_session("/root/data/ug2s_img")
M = m1lf.Method(); M.prepare("/root/data/ud0_img")
T = {k: [] for k in ("megaloc", "disk_query", "lightglue_x_all", "pnp", "total")}
def tick(): torch.cuda.synchronize(); return time.time()
orig_pose = M._pose
acc = {}
def timed_pose(*a, **k):
    t0 = time.time(); r = orig_pose(*a, **k); acc["pnp"] = acc.get("pnp", 0) + time.time() - t0; return r
M._pose = timed_pose
rng = np.random.default_rng(0)
for i in range(0, 80, 2):
    img = cv2.imread(q["images"][i]); prior = q["T"][i][:2, 3] + rng.normal(0, 5, 2)
    acc.clear(); t0 = tick()
    with torch.no_grad(): m1lf.mega_embed(M.mega, [img])
    t1 = tick()
    with torch.no_grad(): M._qf = None; M._disk(m1l.gray_t(img))
    t2 = tick()
    M.localize(img, q["K"], prior_xy=prior); t3 = tick()
    if i >= 4:
        T["megaloc"].append(t1 - t0); T["disk_query"].append(t2 - t1); T["total"].append(t3 - t2); T["pnp"].append(acc.get("pnp", 0))
T["lightglue_x_all"] = [a - b for a, b in zip(T["total"], T["pnp"])]
for k, v in T.items(): print(f"{k:16s} median {1000*np.median(v):7.1f} ms")
print("(total = full localize(); megaloc and disk_query are measured separately and are INSIDE total; lightglue_x_all = total - pnp = everything but PnP)")
