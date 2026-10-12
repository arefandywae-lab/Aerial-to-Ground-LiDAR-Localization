"""One-off patch (repo root): render-and-refine (CRISTAL-style). After the PnP pose, re-render the map at that pose, match the query to that render (tiny viewpoint gap), re-solve PnP
from the new provenance; keep the refined pose only if it has enough inliers. M1LF_REFINE = number of iterations (0 = off, reproduces earlier results)."""
import io


def rw(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:60])
        s = s.replace(a, b, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


rw("vps/m1l.py", [
    ("    def _pose(self, res, K):", "    def _pose(self, res, K, views=None):"),
    ("        res.sort(key=lambda r: -r[0])\n        p2, p3, src = [], [], []",
     "        res.sort(key=lambda r: -r[0])\n        ids_, rt_ = views if views is not None else (self.ids, self.RT)  # views=(ids list, poses list) lets refinement use a fresh render\n        p2, p3, src = [], [], []"),
    ("            pid = self.ids[i][np.round(b[:, 1])", "            pid = ids_[i][np.round(b[:, 1])"),
    ("        top1 = self.RT[res[0][1]]", "        top1 = rt_[res[0][1]]"),
])
rw("vps/m1lf.py", [
    ('PRIOR_R = float(os.environ.get("M1LF_PRIOR_R", 20))',
     'REFINE = int(os.environ.get("M1LF_REFINE", 0))  # render-and-refine iterations after the first PnP (0 = off)\nPRIOR_R = float(os.environ.get("M1LF_PRIOR_R", 20))'),
    ("        Pg = torch.from_numpy(d[\"pts\"]).float().to(m1l.DEV)\n        self.loftr", "        Pg = torch.from_numpy(d[\"pts\"]).float().to(m1l.DEV)\n        self.Pg, self.rgb = Pg, rgb\n        self.loftr"),
    ("            res.append((int(ok.sum()), i, o[\"keypoints0\"][ok].float().cpu().numpy(), o[\"keypoints1\"][ok].float().cpu().numpy()))\n        return self._pose(res, K)",
     """            res.append((int(ok.sum()), i, o["keypoints0"][ok].float().cpu().numpy(), o["keypoints1"][ok].float().cpu().numpy()))
        T, info = self._pose(res, K)
        for _ in range(REFINE if T is not None else 0):  # render at the current estimate, re-match, re-solve; keep only if it holds up
            img_r, ids_r = shade(render_gpu(self.Pg, T, K), self.rgb)
            o = self._match(q, m1l.gray_t(img_r))
            ok = o["confidence"] > m1l.CONF
            T2, info2 = self._pose([(int(ok.sum()), 0, o["keypoints0"][ok].float().cpu().numpy(), o["keypoints1"][ok].float().cpu().numpy())], K, views=([ids_r], [T]))
            if T2 is None or info2.get("inliers", 0) < max(12, 0.5 * info.get("inliers", 0)):
                break
            T, info = T2, dict(info2, refined=1.0)
        return T, info"""),
])
print("patched")
