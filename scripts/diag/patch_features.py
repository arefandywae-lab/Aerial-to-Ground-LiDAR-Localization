"""One-off patch (run from the repo root): log per-query confidence features from the localizer for the learned confidence gate."""
import io


def rw(path, fn):
    s = io.open(path, encoding="utf-8").read()
    s2 = fn(s)
    assert s2 != s, f"no change in {path}"
    io.open(path, "w", encoding="utf-8", newline="\n").write(s2)


NEW_POSE = '''    def _pose(self, res, K):
        """res: [(n_confident_matches, render_idx, query_xy (n,2), render_xy (n,2)), ...] -> (T_cam2world | None, info).
        info carries the numeric features used by the learned confidence gate (scripts/confidence_gate.py)."""
        res.sort(key=lambda r: -r[0])
        p2, p3, src = [], [], []
        for n, i, a, b in res[:TOPK]:
            pid = self.ids[i][np.round(b[:, 1]).astype(int).clip(0, 479), np.round(b[:, 0]).astype(int).clip(0, 639)]
            v = pid >= 0
            p2.append(a[v])
            p3.append(self.P[pid[v]])
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
        proj, _ = cv2.projectPoints(p3[i], rv, tv, K, None)
        pc = p3[i] @ R.T + tv.ravel()
        top1 = self.RT[res[0][1]]
        c = np.clip((np.trace(Tc[:3, :3].T @ top1[:3, :3]) - 1) / 2, -1, 1)
        top2 = res[1][0] if len(res) > 1 else 0
        info = {"inliers": len(i), "n_match": len(p2), "inl_ratio": len(i) / len(p2),
                "top1": res[0][0], "top2": top2, "margin": (res[0][0] - top2) / max(res[0][0], 1),
                "n_renders": len(np.unique(src[i])),
                "spread": float(np.mean(p2[i].std(0)) / 320.0),
                "rep_err": float(np.linalg.norm(proj[:, 0] - p2[i], axis=1).mean()),
                "depth_med": float(np.median(pc[:, 2])),
                "d_render_t": float(np.linalg.norm(Tc[:3, 3] - top1[:3, 3])),
                "d_render_rot": float(np.degrees(np.arccos(c)))}
        return Tc, info
'''


def m1l(s):
    s = s.replace('        self.g, self.ids = [], []\n        for T in s["T"][::STEP]:',
                  '        self.g, self.ids = [], []\n        self.RT = list(s["T"][::STEP])  # camera-to-world pose of every render (virtual-pose subclasses set their own)\n        for T in s["T"][::STEP]:')
    return s[:s.index("    def _pose(self, res, K):")] + NEW_POSE


def m1lf(s):
    s = s.replace("        self.g, self.gs, self.ids = [], [], []\n", "        self.g, self.gs, self.ids, self.RT = [], [], [], []\n")
    return s.replace("                g = m1l.gray_t(img)\n", "                self.RT.append(T)\n                g = m1l.gray_t(img)\n")


def harness(s):
    s = s.replace("        preds, lat, inl = [], [], []", "        preds, lat, inl, infos = [], [], [], []")
    s = s.replace('            inl.append(info.get("inliers", 0))', '            inl.append(info.get("inliers", 0))\n            infos.append(info)')
    old = '        np.save(out.replace(".json", "_err.npy"), np.c_[e, inl_a])  # dt, dr, inliers per query'
    assert old in s
    return s.replace(old, old + '''
        names = sorted({k for i in infos for k in i} - {"inliers"})
        if names:  # per-query confidence features (NaN where the method returned no pose / has no such feature)
            np.save(out.replace(".json", "_feat.npy"), np.array([[i.get(k, np.nan) for k in names] for i in infos], float))
            json.dump({"feature_names": names}, open(out.replace(".json", "_feat_names.json"), "w"))''')


rw("vps/m1l.py", m1l)
rw("vps/m1lf.py", m1lf)
rw("vps/harness.py", harness)
print("patched")
