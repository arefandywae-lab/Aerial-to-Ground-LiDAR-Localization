"""M1-LoFTR: same rendered map-as-images + pixel provenance as m1, but query<->render matching is LoFTR (detector-free,
learned) instead of SIFT. Retrieval = LoFTR match count against every STEP-th render; PnP from the top-K renders' matches."""
import os

import cv2
import numpy as np
import torch
from kornia.feature import LoFTR

from harness import load_session
from m1 import LIDAR_MAP, render

STEP = int(os.environ.get("M1L_STEP", 3))
TOPK, CONF = 5, 0.5
PLANE = int(os.environ.get("M1_PLANE", 0))  # 1 = plane-corrected 3D provenance
PROV = os.environ.get("M1_PROV", "point")  # "ray" = 3D point on the render pixel's own ray at the chosen point's camera depth
DROP_FILLED = int(os.environ.get("M1_DROP_FILLED", 0))  # 1 = ignore correspondences on hole-filled render pixels
DEV = "cuda"


def gray_t(img):
    return torch.from_numpy(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)).float().div(255)[None, None].to(DEV)


def grav_refine(p3, p2, K, Tc0, g_c):
    """Tc0: camera-to-world 4x4 from PnP; g_c: unit gravity direction in the CAMERA frame (down). Returns camera-to-world with pitch/roll fixed by g_c; free: yaw psi and camera centre."""
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation as Rot
    u = -np.asarray(g_c, float) / np.linalg.norm(g_c)  # camera-frame 'up'
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(u, z)
    s = np.linalg.norm(ax)
    Rmin = np.eye(3) if s < 1e-9 else Rot.from_rotvec(ax / s * np.arctan2(s, u @ z)).as_matrix()  # minimal rotation taking u to world up
    M = Tc0[:3, :3] @ Rmin.T
    psi0 = np.arctan2(M[1, 0], M[0, 0])

    def res(x):
        c, sn = np.cos(x[0]), np.sin(x[0])
        R = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ Rmin  # R u = z for every yaw
        Xc = (p3 - x[1:4]) @ R  # world -> camera: R^T (X - t)
        return (np.c_[K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2], K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2]] - p2).ravel()

    sol = least_squares(res, np.r_[psi0, Tc0[:3, 3]], loss="huber", f_scale=2.0, max_nfev=50)
    c, sn = np.cos(sol.x[0]), np.sin(sol.x[0])
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ Rmin
    T[:3, 3] = sol.x[1:4]
    return T


class Method:
    def prepare(self, map_dir):
        s = load_session(map_dir)
        self.K = s["K"]
        d = np.load(LIDAR_MAP)
        self.P = d["pts"].astype(np.float64)
        self.loftr = LoFTR(pretrained="outdoor").to(DEV).eval()
        self.g, self.ids = [], []
        self.RT = list(s["T"][::STEP])  # camera-to-world pose of every render (virtual-pose subclasses set their own)
        for T in s["T"][::STEP]:
            img, ids = render(self.P, d["rgb"], T, self.K)
            self.g.append(gray_t(img))
            self.ids.append(ids)
        print(f"M1L map: {len(self.g)} renders, {len(self.P)} map points")

    @torch.no_grad()
    def localize(self, img, K):
        q = gray_t(img)
        res = []
        for i, g in enumerate(self.g):
            o = self.loftr({"image0": q, "image1": g})
            ok = o["confidence"] > CONF
            res.append((int(ok.sum()), i, o["keypoints0"][ok].cpu().numpy(), o["keypoints1"][ok].cpu().numpy()))
        return self._pose(res, K)

    def _pose(self, res, K, views=None, grav_c=None):
        """res: [(n_confident_matches, render_idx, query_xy (n,2), render_xy (n,2)), ...] -> (T_cam2world | None, info).
        info carries the numeric features used by the learned confidence gate (scripts/confidence_gate.py)."""
        res.sort(key=lambda r: -r[0])
        ids_, rt_ = views if views is not None else (self.ids, self.RT)  # views=(ids list, poses list) lets refinement use a fresh render
        p2, p3, src = [], [], []
        for n, i, a, b in res[:TOPK]:
            pid = ids_[i][np.round(b[:, 1]).astype(int).clip(0, 479), np.round(b[:, 0]).astype(int).clip(0, 639)]
            v = pid >= 0
            dm = getattr(self, "dmask", None)
            if DROP_FILLED and dm is not None and views is None:  # direct-hit mask of the render (bit-packed); filled pixels carry a neighbour's point (~10 px off)
                flat = (np.round(b[:, 1]).astype(int).clip(0, 479) * 640 + np.round(b[:, 0]).astype(int).clip(0, 639))
                v &= np.unpackbits(dm[i])[flat].astype(bool)
            p2.append(a[v])
            X = self.P[pid[v]]
            if PROV == "ray" and v.any():  # place the point on this pixel's own ray (zero reprojection offset); keep the chosen point's camera depth
                Tr = rt_[i]
                z = ((X - Tr[:3, 3]) @ Tr[:3, :3])[:, 2]
                bb = b[v]
                dirc = np.c_[(bb[:, 0] - K[0, 2]) / K[0, 0], (bb[:, 1] - K[1, 2]) / K[1, 1], np.ones(len(bb))]
                X = Tr[:3, 3] + (dirc * z[:, None]) @ Tr[:3, :3].T
            N = getattr(self, "N", None)
            if N is not None and PLANE and v.any():  # plane-corrected provenance (see scripts/diag/patch_plane.py)
                Tr = rt_[i]
                bb = b[v]
                d = np.c_[(bb[:, 0] - K[0, 2]) / K[0, 0], (bb[:, 1] - K[1, 2]) / K[1, 1], np.ones(len(bb))] @ Tr[:3, :3].T
                nn = N[pid[v]]
                nd = np.einsum("ij,ij->i", nn, d)
                with np.errstate(divide="ignore", invalid="ignore"):
                    t = np.einsum("ij,ij->i", nn, X - Tr[:3, 3]) / nd
                Xc = Tr[:3, 3] + t[:, None] * d
                good = (np.abs(nd) / np.linalg.norm(d, axis=1) > 0.25) & (np.linalg.norm(Xc - X, axis=1) < 0.5) & np.isfinite(t)
                X = np.where(good[:, None], Xc, X)
            p3.append(X)
            src.append(np.full(int(v.sum()), i))
        if not p2 or sum(len(x) for x in p2) < 12:
            return None, {"inliers": 0}
        p2, p3, src = np.concatenate(p2).astype(np.float64), np.concatenate(p3), np.concatenate(src)
        ok, rv, tv, inl = cv2.solvePnPRansac(p3, p2, K, None, iterationsCount=2000, reprojectionError=4.0,
                                             flags=cv2.SOLVEPNP_EPNP)
        if not ok or inl is None or len(inl) < 12:
            return None, {"inliers": 0 if inl is None else len(inl)}
        i = inl.ravel()
        rv, tv = cv2.solvePnPRefineLM(p3[i], p2[i], K, None, rv, tv)
        R, _ = cv2.Rodrigues(rv)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, tv.ravel()
        Tc = np.linalg.inv(T)
        if grav_c is not None and len(i) >= 12:  # gravity-aided: pitch/roll from the IMU, solve yaw + position
            Tc = grav_refine(p3[i], p2[i], K, Tc, grav_c)
            T = np.linalg.inv(Tc)
            R = T[:3, :3]
            tv = T[:3, 3:4]
            rv, _ = cv2.Rodrigues(R)
        proj, _ = cv2.projectPoints(p3[i], rv, tv, K, None)
        pc = p3[i] @ R.T + tv.ravel()
        top1 = rt_[res[0][1]]
        c = np.clip((np.trace(Tc[:3, :3].T @ top1[:3, :3]) - 1) / 2, -1, 1)
        top2 = res[1][0] if len(res) > 1 else 0
        self.last_corr = (p2[i].copy(), p3[i].copy())  # inlier correspondences of the final pose (pixels, map points), kept for multi-frame solving (scripts/seq_collect.py)
        info = {"inliers": len(i), "n_match": len(p2), "inl_ratio": len(i) / len(p2),
                "top1": res[0][0], "top2": top2, "margin": (res[0][0] - top2) / max(res[0][0], 1),
                "n_renders": len(np.unique(src[i])),
                "spread": float(np.mean(p2[i].std(0)) / 320.0),
                "rep_err": float(np.linalg.norm(proj[:, 0] - p2[i], axis=1).mean()),
                "depth_med": float(np.median(pc[:, 2])),
                "d_render_t": float(np.linalg.norm(Tc[:3, 3] - top1[:3, 3])),
                "d_render_rot": float(np.degrees(np.arccos(c)))}
        return Tc, info
