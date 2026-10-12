"""CPU painter renderer vs GPU z-buffer renderer: agreement + speed (run inside WSL)."""
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1
import m1lf
from harness import load_session

s = load_session("/root/data/s0_img")
d = np.load(m1.LIDAR_MAP)
P, rgb = d["pts"].astype(np.float64), d["rgb"]
Pg = torch.from_numpy(d["pts"]).float().cuda()
K = s["K"]
idx = (10, 60, 120, 180, 240)


def sync():
    torch.cuda.synchronize()


# speed: warm up then time
m1.render(P, rgb, s["T"][0], K)
m1lf.shade(m1lf.render_gpu(Pg, s["T"][0], K), rgb)
sync()
t = time.perf_counter()
for i in idx:
    m1.render(P, rgb, s["T"][i], K)
tc = (time.perf_counter() - t) / len(idx)
t = time.perf_counter()
for i in idx:
    ids = m1lf.render_gpu(Pg, s["T"][i], K)
sync()
tg_core = (time.perf_counter() - t) / len(idx)
t = time.perf_counter()
for i in idx:
    m1lf.shade(m1lf.render_gpu(Pg, s["T"][i], K), rgb)
sync()
tg = (time.perf_counter() - t) / len(idx)
print(f"per render: CPU painter {tc*1e3:.0f} ms | GPU z-buffer core {tg_core*1e3:.0f} ms | GPU incl. CPU hole-fill/shade {tg*1e3:.0f} ms")

# agreement
for i in idx[:3]:
    ic, idc = m1.render(P, rgb, s["T"][i], K)
    ig, idg = m1lf.shade(m1lf.render_gpu(Pg, s["T"][i], K), rgb)
    both = (idc >= 0) & (idg >= 0)
    same = (idc == idg)[both].mean()
    # compare 3D positions of provenance (different ids can still be the same surface)
    dd = np.linalg.norm(P[idc[both]] - P[idg[both]], axis=1)
    print(f"pose {i}: filled px CPU {(idc>=0).mean():.3f} GPU {(idg>=0).mean():.3f} | same id {same:.3f} | 3D gap median {np.median(dd)*100:.1f} cm p90 {np.percentile(dd,90)*100:.1f} cm | mean |img diff| {np.abs(ic.astype(int)-ig.astype(int)).mean():.2f}")

# scaling: 10x points (a 200x200 m urban map is this order)
Pbig = torch.cat([Pg + torch.randn_like(Pg) * 0.01] * 10)
sync()
t = time.perf_counter()
ids = m1lf.render_gpu(Pbig, s["T"][100], K)
sync()
print(f"GPU core with {len(Pbig)/1e6:.1f} M points: {(time.perf_counter()-t)*1e3:.0f} ms")
Pbc = np.concatenate([P] * 10)
t = time.perf_counter()
m1.render(Pbc, np.concatenate([rgb] * 10), s["T"][100], K)
print(f"CPU painter with {len(Pbc)/1e6:.1f} M points: {(time.perf_counter()-t)*1e3:.0f} ms")
