"""One-off patch (repo root): ray-consistent provenance + dropping hole-filled correspondences, fixing what scripts/audit_provenance.py measured:
 - the provenance point of a splatted pixel reprojects ~3 px (p90 4.7) from its pixel, ground points +1.2 px low; hole-filled pixels ~10 px (p90 15) off
Fix: M1_PROV=ray places the 3D point on the render pixel's own viewing ray at the camera-z of the chosen map point (reprojection offset exactly 0, only the depth keeps its error);
M1_DROP_FILLED=1 ignores correspondences that land on hole-filled pixels (direct-hit mask stored per view). Defaults reproduce all earlier results."""
import io


def rw(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:60])
        s = s.replace(a, b, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


rw("vps/m1l.py", [
    ('PLANE = int(os.environ.get("M1_PLANE", 0))  # 1 = plane-corrected 3D provenance\n',
     'PLANE = int(os.environ.get("M1_PLANE", 0))  # 1 = plane-corrected 3D provenance\nPROV = os.environ.get("M1_PROV", "point")  # "ray" = 3D point on the render pixel\'s own ray at the chosen point\'s camera depth\nDROP_FILLED = int(os.environ.get("M1_DROP_FILLED", 0))  # 1 = ignore correspondences on hole-filled render pixels\n'),
    ("            v = pid >= 0\n            p2.append(a[v])\n            X = self.P[pid[v]]\n",
     """            v = pid >= 0
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
"""),
])
rw("vps/m1lf.py", [
    ("        self.g, self.gs, self.ids, self.RT, desc, buf = [], [], [], list(views), [], []\n",
     "        self.g, self.gs, self.ids, self.RT, desc, buf = [], [], [], list(views), [], []\n        self.dmask = []  # bit-packed direct-hit masks (pixels hit by a splat, before hole filling)\n"),
    ("            img, ids = shade(render_gpu(Pg, T, self.K), rgb)\n            gray = cv2.cvtColor",
     "            ids0 = render_gpu(Pg, T, self.K)\n            self.dmask.append(np.packbits(ids0 >= 0))\n            img, ids = shade(ids0, rgb)\n            gray = cv2.cvtColor"),
])
print("patched")
