"""M1-LoFTR-fast: m1l with the three speed-ups that need no new downloads.
 1. GPU renderer: true z-buffer via scatter_reduce(amin) instead of the numpy painter's-order approximation (hole fill/shading shared with m1).
 2. LoFTR in fp16 (torch.autocast).
 3. Coarse-to-fine retrieval: batched LoFTR at half resolution against ALL renders ranks them; full-resolution LoFTR runs only on the
    top-N, and PnP uses the top-K of those.
Env knobs: M1LF_FP16=0/1, M1LF_TOPN (full-res candidates), M1LF_COARSE=0 to skip the coarse stage (all renders at full res)."""
import os

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from kornia.feature import LoFTR

import m1l
from harness import load_session
from m1 import FILL_PX, SPLAT_M, ZFAR, shade  # noqa: F401  (FILL_PX re-exported for tuning scripts)

RMAX = int(os.environ.get("M1_RMAX", 4))  # max splat radius in pixels (cost grows with (2*RMAX+1)^2)

FP16 = int(os.environ.get("M1LF_FP16", 1))
TOPN = int(os.environ.get("M1LF_TOPN", 12))
COARSE = int(os.environ.get("M1LF_COARSE", 1))
BATCH = int(os.environ.get("M1LF_BATCH", 8))
MATCHER = os.environ.get("M1LF_MATCHER", "loftr")  # loftr | xfeat (kornia XFeat, sparse; no coarse stage: set M1LF_COARSE=0 and M1LF_K to the shortlist size)
RMATCHER = os.environ.get("M1LF_REFINE_MATCHER", MATCHER)  # matcher of the render-at-estimate refine stage (hybrid: xfeat to find the pose, loftr to refine it)
LGFP16 = os.environ.get("M1LF_LGFP16") == "1"  # LightGlue under fp16 autocast
LGBATCH = int(os.environ.get("M1LF_LGBATCH", 0))  # >0: DISK+LightGlue on this many shortlisted views per batched call
MAXD = float(os.environ.get("M1LF_MAXD", 0))  # >0: reject poses farther than this (m) from the best retrieved view
LEAK = float(os.environ.get("M1_LEAK", 0))  # >0: relative depth tolerance of the background-leak filter in render_gpu (0 = off)
HYP = int(os.environ.get("M1LF_HYP", 0))  # >0: also keep a separate PnP pose for each of the best HYP shortlisted views (self.last_hyp)
RETR = os.environ.get("M1LF_RETR", "none")  # none | megaloc: vector shortlist before the LoFTR stages
SHORT = int(os.environ.get("M1LF_K", 50))  # shortlist size
VIEWS = os.environ.get("M1_VIEWS", "")  # .npy of (N,4,4) camera-to-world virtual viewpoints (vps/viewpoints.py); overrides STEP/YAWS
YAWS = [float(v) for v in os.environ.get("M1LF_YAWS", "0").split(",")]  # extra virtual viewpoints: map pose rotated about world z by these degrees


def render_gpu(P, T, K, size=(640, 480)):
    """P: (N,3) float32 cuda tensor. -> int32 point-index map (h,w), -1 empty. Nearest point per pixel (z-buffer)."""
    w, h = size
    fx, fy, cx, cy = (float(K[0, 0]), float(K[1, 1]), float(K[0, 2]), float(K[1, 2]))
    Tt = torch.as_tensor(T, dtype=torch.float32, device=P.device)
    pc = (P - Tt[:3, 3]) @ Tt[:3, :3]
    z = pc[:, 2]
    vis = torch.nonzero((z > 0.5) & (z < ZFAR)).squeeze(1)
    zv = z[vis]
    u = torch.round(fx * pc[vis, 0] / zv + cx).long()
    v = torch.round(fy * pc[vis, 1] / zv + cy).long()
    r = torch.clamp(torch.round(fx * SPLAT_M / zv), 0, RMAX).long()
    pix, dep, pid = [], [], []
    for du in range(-RMAX, RMAX + 1):
        for dv in range(-RMAX, RMAX + 1):
            m = r >= max(abs(du), abs(dv))  # square splat, same footprint as the CPU renderer
            uu, vv = u[m] + du, v[m] + dv
            ok = (uu >= 0) & (uu < w) & (vv >= 0) & (vv < h)
            pix.append(vv[ok] * w + uu[ok])
            dep.append(zv[m][ok])
            pid.append(vis[m][ok])
    pix, dep, pid = torch.cat(pix), torch.cat(dep), torch.cat(pid)
    zb = torch.full((h * w,), float("inf"), device=P.device).scatter_reduce(0, pix, dep, "amin")
    win = dep <= zb[pix]
    ids = torch.full((h * w,), -1, dtype=torch.int64, device=P.device)
    ids[pix[win]] = pid[win]
    if LEAK > 0:  # background-leak filter (CRISTAL, arXiv 2511.16349: hierarchical depth filter): a far point that shows through gaps between near points is removed, the hole is then filled by shade()
        Z = zb.view(1, 1, h, w)
        Zf = torch.where(torch.isinf(Z), torch.full_like(Z, 1e9), Z)
        leak = torch.zeros_like(Zf, dtype=torch.bool)
        for k in (5, 11):
            zmin = -F.max_pool2d(-Zf, k, 1, k // 2)
            leak |= (Zf < 1e8) & (Zf - zmin > LEAK * zmin + 0.5)
        ids.view(h, w)[leak[0, 0]] = -1
    return ids.view(h, w).cpu().numpy().astype(np.int32)


MEAN = STD = None


def _norm():
    global MEAN, STD
    if MEAN is None:
        MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).cuda()
        STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).cuda()
    return MEAN, STD


@torch.inference_mode()
def mega_embed(model, bgr_list):
    """MegaLoc descriptors (L2-normalised, 8448-d) of BGR uint8 images; 238x322 input keeps the 4:3 aspect (multiples of 14)."""
    mean, std = _norm()
    x = torch.from_numpy(np.stack([cv2.cvtColor(b, cv2.COLOR_BGR2RGB) for b in bgr_list])).cuda().permute(0, 3, 1, 2).float() / 255
    x = F.interpolate(x, size=(238, 322), mode="bilinear", antialias=True, align_corners=False)
    return model((x - mean) / std)


REFINE = int(os.environ.get("M1LF_REFINE", 0))  # render-and-refine iterations after the first PnP (0 = off)
PRIOR_R = float(os.environ.get("M1LF_PRIOR_R", 20))  # m, candidate radius around the prior when one is given


class Method(m1l.Method):
    uses_prior = True

    def prepare(self, map_dir):
        s = load_session(map_dir)
        self.K = s["K"]
        d = np.load(m1l.LIDAR_MAP)
        self.P = d["pts"].astype(np.float64)
        rgb = d["rgb"]
        Pg = torch.from_numpy(d["pts"]).float().to(m1l.DEV)
        self.Pg, self.rgb = Pg, rgb
        self.N = d["normals"].astype(np.float64) if m1l.PLANE else None
        self.loftr = LoFTR(pretrained="outdoor").to(m1l.DEV).eval()
        if "xfeat" in (MATCHER, RMATCHER):
            from kornia.feature import XFeat
            self.xf = XFeat.from_pretrained().to(m1l.DEV).eval()
        if "disklg" in (MATCHER, RMATCHER):  # DISK keypoints + LightGlue; features of the cached renders are computed once in prepare()
            from kornia.feature import DISK, LightGlue
            self.disk = DISK.from_pretrained("depth").to(m1l.DEV).eval()
            self.lg = LightGlue("disk").to(m1l.DEV).eval()
            self.df, self._qf = [], None
        if RETR == "megaloc":
            self.mega = torch.hub.load("gmberton/MegaLoc", "get_trained_model", trust_repo=True).cuda().eval()
        views = []
        if VIEWS:
            views = list(np.load(VIEWS))
        else:
            for T0 in s["T"][::m1l.STEP]:
                for yaw in YAWS:
                    T = T0.copy()
                    c, sn = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
                    T[:3, :3] = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ T0[:3, :3]  # same position, yawed camera (the map has 360 deg of geometry)
                    views.append(T)
        self.g, self.gs, self.ids, self.RT, desc, buf = [], [], [], list(views), [], []
        self.dmask = []  # bit-packed direct-hit masks (pixels hit by a splat, before hole filling)
        for T in views:
            ids0 = render_gpu(Pg, T, self.K)
            self.dmask.append(np.packbits(ids0 >= 0))
            img, ids = shade(ids0, rgb)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            self.g.append(torch.from_numpy(gray)[None, None])  # uint8 on the CPU: identical values to gray/255 after .float()/255, 4x smaller, off the GPU
            self.gs.append(F.interpolate(m1l.gray_t(img), size=(240, 320), mode="bilinear", antialias=True))
            self.ids.append(ids)
            if MATCHER == "disklg":
                with torch.no_grad():
                    f = self._disk(torch.from_numpy(gray)[None, None].to(m1l.DEV).float().div(255))
                self.df.append((f.keypoints.half().cpu(), f.descriptors.half().cpu()))
            if RETR == "megaloc":
                buf.append(img)
                if len(buf) == 32:
                    desc.append(mega_embed(self.mega, buf)), buf.clear()
        if buf:
            desc.append(mega_embed(self.mega, buf))
        self.pv = np.array([T[:3, 3] for T in self.RT])
        self.gs = torch.cat(self.gs)
        self.desc = torch.cat(desc) if desc else None
        print(f"M1LF map: {len(self.g)} renders, {len(self.P)} map points, fp16={FP16} coarse={COARSE} topn={TOPN} retr={RETR} k={SHORT} "
              f"views={'file' if VIEWS else f'yaws={YAWS} step={m1l.STEP}'}")

    def _g(self, i):
        return self.g[i].to(m1l.DEV).float().div(255)

    def _match(self, a, b):
        with torch.autocast("cuda", dtype=torch.float16, enabled=bool(FP16)):
            return self.loftr({"image0": a, "image1": b})

    def _disk(self, g):
        return self.disk(g.repeat(1, 3, 1, 1), 2048, pad_if_not_divisible=True)[0]

    def _lg(self, a, b, vi):
        if self._qf is None:
            self._qf = self._disk(a)
        fa = self._qf
        if vi is None:
            fb = self._disk(b)
            kb, db = fb.keypoints, fb.descriptors
        else:
            kb, db = (x.to(m1l.DEV).float() for x in self.df[vi])
        sz = lambda g: torch.tensor([[g.shape[-1], g.shape[-2]]], device=g.device).float()
        with torch.autocast("cuda", dtype=torch.float16, enabled=LGFP16):
            m = self.lg({"image0": {"keypoints": fa.keypoints[None], "descriptors": fa.descriptors[None], "image_size": sz(a)},
                         "image1": {"keypoints": kb[None], "descriptors": db[None], "image_size": sz(b)}})["matches"][0]
        return fa.keypoints[m[:, 0]].float().cpu().numpy(), kb[m[:, 1]].float().cpu().numpy()

    def _lg_batch(self, a, idx):
        """DISK+LightGlue of the query against several cached renders in ONE batched call (the per-pair call is launch-bound: ~15 ms per pair).
        Renders with fewer keypoints than the largest are padded by repeating their first keypoint (duplicates cannot create extra true matches
        of a different point; a matched duplicate keeps the same pixel pair). Returns [(kp_query, kp_render)] per idx."""
        if self._qf is None:
            self._qf = self._disk(a)
        fa = self._qf
        n = max([self.df[i][0].shape[0] for i in idx] + [fa.keypoints.shape[0]])  # kornia's batched LightGlue needs equal keypoint counts on both sides
        qk, qd = fa.keypoints, fa.descriptors
        if qk.shape[0] < n:
            qk = torch.cat([qk, qk[:1].expand(n - qk.shape[0], -1)], 0)
            qd = torch.cat([qd, qd[:1].expand(n - qd.shape[0], -1)], 0)
        kb, db = [], []
        for i in idx:
            k, d = (x.to(m1l.DEV).float() for x in self.df[i])
            if k.shape[0] < n:
                k = torch.cat([k, k[:1].expand(n - k.shape[0], -1)], 0)
                d = torch.cat([d, d[:1].expand(n - d.shape[0], -1)], 0)
            kb.append(k); db.append(d)
        kb, db = torch.stack(kb), torch.stack(db)
        B = len(idx)
        if os.environ.get("LGDBG"): print("DBG", fa.keypoints.shape, fa.descriptors.shape, kb.shape, db.shape, flush=True)
        sz = lambda g: torch.tensor([[g.shape[-1], g.shape[-2]]], device=g.device).float().repeat(B, 1)
        out = self.lg({"image0": {"keypoints": qk[None].repeat(B, 1, 1), "descriptors": qd[None].repeat(B, 1, 1), "image_size": sz(a)},
                       "image1": {"keypoints": kb, "descriptors": db, "image_size": sz(a)}})
        res = []
        for b in range(B):
            m = out["matches"][b]
            res.append((qk[m[:, 0]].float().cpu().numpy(), kb[b][m[:, 1]].float().cpu().numpy()))
        return res

    def _kp(self, a, b, matcher=None, vi=None):
        """matched keypoints (query, render) of two (1,1,H,W) gray tensors with the configured matcher"""
        if (matcher or MATCHER) == "disklg":
            return self._lg(a, b, vi)
        if (matcher or MATCHER) == "xfeat":
            p0, p1 = self.xf.match_xfeat(a.repeat(1, 3, 1, 1), b.repeat(1, 3, 1, 1))
            return p0.float().cpu().numpy(), p1.float().cpu().numpy()
        o = self._match(a, b)
        ok = o["confidence"] > m1l.CONF
        return o["keypoints0"][ok].float().cpu().numpy(), o["keypoints1"][ok].float().cpu().numpy()

    @torch.no_grad()
    def localize(self, img, K, prior_xy=None, grav_c=None):
        q = m1l.gray_t(img)
        self._qf = None
        n = len(self.g)
        pool = list(range(n))
        near = np.empty(0, int)
        if prior_xy is not None:  # only views near the prior are candidates (a tile-streaming robot would only have those loaded)
            near = np.where(np.linalg.norm(self.pv[:, :2] - prior_xy, axis=1) < PRIOR_R)[0]
        if len(near):
            if self.desc is not None:
                sim = mega_embed(self.mega, [img]) @ self.desc[torch.as_tensor(near, device=self.desc.device)].T
                near = near[torch.topk(sim[0], min(SHORT, len(near))).indices.cpu().numpy()]
            pool = near.tolist()
        elif prior_xy is not None and os.environ.get("M1LF_PRIOR_STRICT") == "1":  # a prior was given but no cached view lies near it: no pose, never fall back to the whole city
            return None, {"inliers": 0}
        elif self.desc is not None:  # global retrieval: cosine similarity against every render descriptor, keep the top SHORT
            sim = mega_embed(self.mega, [img]) @ self.desc.T
            pool = torch.topk(sim[0], min(SHORT, n)).indices.tolist()
        cand = pool
        if COARSE and len(pool) > TOPN:
            qs = F.interpolate(q, size=(240, 320), mode="bilinear", antialias=True)
            cnt = torch.zeros(len(pool), device=q.device)
            for s in range(0, len(pool), BATCH):
                idx = pool[s:s + BATCH]
                o = self._match(qs.expand(len(idx), -1, -1, -1).contiguous(), self.gs[idx])
                good = o["confidence"] > m1l.CONF
                cnt[s:s + len(idx)] = torch.bincount(o["batch_indexes"][good], minlength=len(idx)).float()
            cand = [pool[j] for j in torch.topk(cnt, min(TOPN, len(pool))).indices.tolist()]
        res = []
        if MATCHER == "disklg" and LGBATCH:
            for s0 in range(0, len(cand), LGBATCH):
                part = cand[s0:s0 + LGBATCH]
                for i, (k0, k1) in zip(part, self._lg_batch(q, part)):
                    res.append((len(k0), i, k0, k1))
        else:
            for i in cand:
                k0, k1 = self._kp(q, self._g(i), vi=i if MATCHER == "disklg" else None)
                res.append((len(k0), i, k0, k1))
        self.last_hyp = None
        if HYP:  # multi-hypothesis output: one PnP pose per shortlisted view (best HYP by match count), for the particle filter (scripts/seq_collect.py)
            hyp = []
            for r in sorted(res, key=lambda r: -r[0])[:HYP]:
                Th, ih = self._pose([r], K)
                hyp.append((Th if Th is not None else np.full((4, 4), np.nan), ih.get("inliers", 0)))
            self.last_hyp = hyp
        T, info = self._pose(res, K, grav_c=grav_c)
        for _ in range(REFINE if T is not None else 0):  # render at the current estimate, re-match, re-solve; keep only if it holds up
            img_r, ids_r = shade(render_gpu(self.Pg, T, K), self.rgb)
            k0, k1 = self._kp(q, m1l.gray_t(img_r), RMATCHER)
            T2, info2 = self._pose([(len(k0), 0, k0, k1)], K, views=([ids_r], [T]), grav_c=grav_c)
            if T2 is None or info2.get("inliers", 0) < max(12, 0.5 * info.get("inliers", 0)):
                break
            T, info = T2, dict(info2, refined=1.0)
        if MAXD > 0 and T is not None and info.get("d_render_t", 0) > MAXD:  # the pose lies far from the view it was matched in: an aliasing outlier (offline: removes 64-84 % of wrong poses at 8 m)
            return None, dict(info, rejected_far=1.0, inliers=0)
        return T, info
