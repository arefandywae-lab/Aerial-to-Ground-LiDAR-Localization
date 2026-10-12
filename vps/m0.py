"""M0: visual-only reference. SIFT map triangulated from mapping images with GT poses (known-pose SfM),
descriptor-voting retrieval -> 2D-3D matching in the top-k keyframes -> PnP+RANSAC.
(Known poses replace COLMAP's pose estimation; for a sim reference that is the fair ceiling.)"""
import cv2
import numpy as np

from harness import load_session

NFEAT, RATIO, TOPK = 2000, 0.8, 5


def sift():
    return cv2.SIFT_create(nfeatures=NFEAT, contrastThreshold=0.02)


def proj(K, T_c2w):
    Tcw = np.linalg.inv(T_c2w)
    return K @ Tcw[:3]


def triangulate(kp_a, kp_b, d_a, d_b, Pa, Pb, K, Ta, Tb):
    """ratio-test matches between two keyframes -> (idx_a, X) for well-conditioned points."""
    if d_a is None or d_b is None or len(d_a) < 2 or len(d_b) < 2:
        return np.empty(0, int), np.empty((0, 3))
    bf = cv2.BFMatcher()
    mm = [p[0] for p in bf.knnMatch(d_a, d_b, k=2) if len(p) == 2 and p[0].distance < RATIO * p[1].distance]
    if len(mm) < 8:
        return np.empty(0, int), np.empty((0, 3))
    ia = np.array([m.queryIdx for m in mm])
    pa = np.float64([kp_a[m.queryIdx] for m in mm])
    pb = np.float64([kp_b[m.trainIdx] for m in mm])
    X = cv2.triangulatePoints(Pa, Pb, pa.T, pb.T)
    X = (X[:3] / X[3]).T
    keep = np.ones(len(X), bool)
    for P, p in ((Pa, pa), (Pb, pb)):
        h = (P @ np.c_[X, np.ones(len(X))].T)
        keep &= h[2] > 0.3
        keep &= np.linalg.norm((h[:2] / h[2]).T - p, axis=1) < 2.0
    ra, rb = X - Ta[:3, 3], X - Tb[:3, 3]  # triangulation angle
    cosang = (ra * rb).sum(1) / (np.linalg.norm(ra, axis=1) * np.linalg.norm(rb, axis=1) + 1e-9)
    keep &= np.degrees(np.arccos(np.clip(cosang, -1, 1))) > 1.0
    return ia[keep], X[keep]


class Method:
    def prepare(self, map_dir):
        self._index(*self._keyframes(map_dir))

    def _keyframes(self, map_dir):
        s = load_session(map_dir)
        self.K = s["K"]
        f = sift()
        feats = []
        for p in s["images"]:
            kp, d = f.detectAndCompute(cv2.imread(p, 0), None)
            feats.append(([k.pt for k in kp], d if d is not None else np.empty((0, 128), np.float32)))
        desc, pts = [], []
        for i, (kp, d) in enumerate(feats):
            Pi = proj(self.K, s["T"][i])
            best = {}
            for j in (i - 2, i - 1, i + 1, i + 2):
                if not 0 <= j < len(feats):
                    continue
                ia, X = triangulate(kp, feats[j][0], d, feats[j][1], Pi, proj(self.K, s["T"][j]),
                                    self.K, s["T"][i], s["T"][j])
                for a, x in zip(ia, X):
                    best.setdefault(a, x)  # first valid triangulation wins
            if best:
                idx = np.array(list(best))
                desc.append(d[idx])
                pts.append(np.array([best[a] for a in idx]))
        return desc, pts

    def _index(self, desc, pts):
        """desc/pts: per-keyframe (Nk,128) descriptors and (Nk,3) world points -> flat FLANN index + keyframe id per point."""
        self.desc, self.pts = desc, pts
        self.ids = np.concatenate([np.full(len(d), n) for n, d in enumerate(self.desc)])
        self.D = np.concatenate(self.desc).astype(np.float32)
        self.X = np.concatenate(self.pts)
        self.flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=4), dict(checks=64))
        self.flann.add([self.D])
        self.flann.train()
        print(f"M0 map: {len(self.desc)} keyframes, {len(self.X)} 3D points")

    def localize(self, img, K):
        kp, d = sift().detectAndCompute(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), None)
        if d is None or len(kp) < 12:
            return None, {}
        m = [p[0] for p in self.flann.knnMatch(d.astype(np.float32), k=2)
             if len(p) == 2 and p[0].distance < RATIO * p[1].distance]  # ponytail: global ratio test, ceiling = repetitive texture
        if len(m) < 12:
            return None, {}
        votes = np.bincount(self.ids[[a.trainIdx for a in m]], minlength=len(self.desc))
        # 2D-3D from the voted-for keyframes only (retrieval by descriptor voting)
        top = set(np.argsort(-votes)[:TOPK])
        sel = [a for a in m if self.ids[a.trainIdx] in top]
        if len(sel) < 12:
            return None, {}
        p2 = np.float64([kp[a.queryIdx].pt for a in sel])
        p3 = self.X[[a.trainIdx for a in sel]]
        ok, rv, tv, inl = cv2.solvePnPRansac(p3, p2, K, None, iterationsCount=2000, reprojectionError=4.0,
                                             flags=cv2.SOLVEPNP_EPNP)
        if not ok or inl is None or len(inl) < 12:
            return None, {"inliers": 0 if inl is None else len(inl)}
        i = inl.ravel()
        rv, tv = cv2.solvePnPRefineLM(p3[i], p2[i], K, None, rv, tv)
        R, _ = cv2.Rodrigues(rv)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = R, tv.ravel()
        return np.linalg.inv(T), {"inliers": len(inl)}
