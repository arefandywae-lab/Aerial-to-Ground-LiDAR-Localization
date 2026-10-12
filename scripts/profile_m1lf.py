"""Where do the ~2.3 s per query go in M1-LoFTR with MegaLoc retrieval? Times each stage with GPU synchronisation over the first N queries of a session.
usage: profile_m1lf.py QUERY_SESSION [N=30]   env as vps/m1lf.py (M1LF_RETR=megaloc, M1LF_K, M1LF_TOPN, M1LF_FP16, ...)"""
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, "/mnt/a/SlamProject/vps")
import m1l
import m1lf
from harness import load_session

q = load_session(f"/root/data/{sys.argv[1]}_img")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 30
M = m1lf.Method()
M.prepare("/root/data/s0v2_img")
imgs = [cv2.imread(p) for p in q["images"][:N]]
for im in imgs[:3]:
    M.localize(im, q["K"])  # warm-up


def sync():
    torch.cuda.synchronize()
    return time.perf_counter()


acc = {k: [] for k in ("embed+topk", "coarse", "full", "pnp", "total")}
with torch.no_grad():
    for img in imgs:
        t0 = sync()
        qg = m1l.gray_t(img)
        n = len(M.g)
        pool = list(range(n))
        if M.desc is not None:
            sim = m1lf.mega_embed(M.mega, [img]) @ M.desc.T
            pool = torch.topk(sim[0], min(m1lf.SHORT, n)).indices.tolist()
        t1 = sync()
        cand = pool
        if m1lf.COARSE and len(pool) > m1lf.TOPN:
            qs = F.interpolate(qg, size=(240, 320), mode="bilinear", antialias=True)
            cnt = torch.zeros(len(pool), device=qg.device)
            for s in range(0, len(pool), m1lf.BATCH):
                idx = pool[s:s + m1lf.BATCH]
                o = M._match(qs.expand(len(idx), -1, -1, -1).contiguous(), M.gs[idx])
                good = o["confidence"] > m1l.CONF
                cnt[s:s + len(idx)] = torch.bincount(o["batch_indexes"][good], minlength=len(idx)).float()
            cand = [pool[j] for j in torch.topk(cnt, min(m1lf.TOPN, len(pool))).indices.tolist()]
        t2 = sync()
        res = []
        for i in cand:
            o = M._match(qg, M._g(i))
            ok = o["confidence"] > m1l.CONF
            res.append((int(ok.sum()), i, o["keypoints0"][ok].float().cpu().numpy(), o["keypoints1"][ok].float().cpu().numpy()))
        t3 = sync()
        M._pose(res, q["K"])
        t4 = time.perf_counter()
        for k, v in zip(acc, (t1 - t0, t2 - t1, t3 - t2, t4 - t3, t4 - t0)):
            acc[k].append(v)
print(f"queries {N}, shortlist K={m1lf.SHORT}, top-N full-res {m1lf.TOPN}, fp16={m1lf.FP16}, coarse batch {m1lf.BATCH}")
for k, v in acc.items():
    print(f"  {k:11s} median {1e3*np.median(v):7.0f} ms   p95 {1e3*np.percentile(v, 95):7.0f} ms")
