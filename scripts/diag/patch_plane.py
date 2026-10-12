"""One-off patch (repo root): plane-corrected provenance. A render pixel's 3D point is the (voxel-centre) map point nearest the camera, up to ~0.12 m off the true surface at 0.25 m voxels.
With the map's PCA normals, intersect the pixel's viewing ray (render camera pose + K) with the plane through that point: X = o + t d, t = n.(p - o)/(n.d).
Used only when the ray is not grazing (|n.d| > 0.25) and the correction is < 0.5 m; otherwise the original point. M1_PLANE=1 enables (default off: reproduces earlier results)."""
import io


def rw(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:60])
        s = s.replace(a, b, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


rw("vps/m1l.py", [
    ("            v = pid >= 0\n            p2.append(a[v])\n            p3.append(self.P[pid[v]])\n",
     """            v = pid >= 0
            p2.append(a[v])
            X = self.P[pid[v]]
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
"""),
    ('TOPK, CONF = 5, 0.5\n', 'TOPK, CONF = 5, 0.5\nPLANE = int(os.environ.get("M1_PLANE", 0))  # 1 = plane-corrected 3D provenance\n'),
])
rw("vps/m1lf.py", [
    ("        self.Pg, self.rgb = Pg, rgb\n", "        self.Pg, self.rgb = Pg, rgb\n        self.N = d[\"normals\"].astype(np.float64) if m1l.PLANE else None\n"),
])
print("patched")
