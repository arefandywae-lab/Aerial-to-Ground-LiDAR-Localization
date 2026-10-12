"""Matcher swap on the oracle views (perfect retrieval) of route 2: LoFTR (baseline) vs kornia XFeat / XFeat* — pose success and ms per pair.
env as urban_diag.py (DIAG_QUERIES). usage: matcher_bench.py [loftr xfeat xfeatstar]"""
import os, sys, time
from concurrent.futures import ThreadPoolExecutor
import cv2, numpy as np, torch
sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1l, m1lf
from harness import load_session, pose_err
from kornia.feature import XFeat

q = load_session(os.environ.get("DIAG_QUERIES", "/root/data/ug2s_img"))
M = m1lf.Method(); M.prepare("/root/data/ud0_img")
pv = np.array([T[:3, 3] for T in M.RT]); hv = np.array([np.degrees(np.arctan2(T[1, 2], T[0, 2])) for T in M.RT])
pq = np.array([T[:3, 3] for T in q["T"]]); hq = np.array([np.degrees(np.arctan2(T[1, 2], T[0, 2])) for T in q["T"]])
dpos = np.linalg.norm(pq[:, None] - pv[None], axis=2); dyaw = np.abs((hq[:, None] - hv[None] + 180) % 360 - 180)
oracle = np.argmin(dpos + 0.05 * dyaw, axis=1)
with ThreadPoolExecutor(8) as ex: imgs = list(ex.map(cv2.imread, q["images"]))
xf = XFeat.from_pretrained().to("cuda").eval() if hasattr(XFeat, "from_pretrained") else XFeat().cuda().eval()

def loftr(i, j):
    o = M._match(m1l.gray_t(imgs[i]), M._g(j)); ok = o["confidence"] > m1l.CONF
    return o["keypoints0"][ok].float().cpu().numpy(), o["keypoints1"][ok].float().cpu().numpy()

def rgb(x): return torch.from_numpy(x).permute(2, 0, 1)[None].float().cuda() / 255
def xfeat(i, j, star=False):
    a = rgb(cv2.cvtColor(imgs[i], cv2.COLOR_BGR2RGB)); g = M._g(j); g = g.reshape(1, 1, *g.shape[-2:]); b = g.repeat(1, 3, 1, 1)
    r = xf.match_xfeat_star(a, b) if star else xf.match_xfeat(a, b)
    r = r[0] if isinstance(r, (list, tuple)) and len(r) == 1 else r
    return np.asarray(r[0].cpu() if hasattr(r[0], "cpu") else r[0], np.float32), np.asarray(r[1].cpu() if hasattr(r[1], "cpu") else r[1], np.float32)

from kornia.feature import DISK, LightGlue
disk = DISK.from_pretrained("depth").cuda().eval(); lg = LightGlue("disk").cuda().eval()
def dlg(i, j):
    a = rgb(cv2.cvtColor(imgs[i], cv2.COLOR_BGR2RGB)); g = M._g(j); g = g.reshape(1, 1, *g.shape[-2:]); b = g.repeat(1, 3, 1, 1)
    fa, fb = disk(a, 2048, pad_if_not_divisible=True)[0], disk(b, 2048, pad_if_not_divisible=True)[0]
    d = lambda f, im: {"keypoints": f.keypoints[None], "descriptors": f.descriptors[None], "image_size": torch.tensor([[im.shape[-1], im.shape[-2]]], device="cuda").float()}
    o = lg({"image0": d(fa, a), "image1": d(fb, b)})
    m = o["matches"][0]
    return fa.keypoints[m[:, 0]].cpu().numpy(), fb.keypoints[m[:, 1]].cpu().numpy()
fns = {"loftr": loftr, "xfeat": xfeat, "disklg": dlg, "xfeatstar": lambda i, j: xfeat(i, j, True)}
for name in (sys.argv[1:] or fns):
    rows, ts = [], []
    with torch.no_grad():
        fns[name](0, int(oracle[0]))
        for i in range(len(imgs)):
            j = int(oracle[i]); torch.cuda.synchronize(); t0 = time.time()
            try: p0, p1 = fns[name](i, j)
            except Exception as e: print(name, "error", repr(e)[:200]); break
            torch.cuda.synchronize(); ts.append(time.time() - t0)
            T, info = M._pose([(len(p0), j, p0, p1)], q["K"])
            dt, dr = pose_err(T, q["T"][i]) if T is not None else (np.inf, np.inf)
            rows.append((len(p0), dt, dr))
    r = np.array(rows)
    if len(r): print(f"{name:10s} n={len(r)} | pose {np.isfinite(r[:,1]).mean():.1%} | (5m,10deg) {np.mean((r[:,1]<=5)&(r[:,2]<=10)):.1%} | (0.5m,5deg) {np.mean((r[:,1]<=.5)&(r[:,2]<=5)):.1%} | median matches {np.median(r[:,0]):.0f} | {1000*np.median(ts):.0f} ms/pair")
