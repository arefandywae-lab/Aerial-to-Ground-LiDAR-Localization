"""One-off patch (repo root): prior-aided mode. The harness can hand each query a noisy position prior (GT + gaussian xy noise, simulating odometry/last-fix uncertainty);
m1lf then restricts candidate views to those within PRIOR_R of the prior (what tile streaming would load). Disabled unless PRIOR_SIGMA > 0."""
import io


def rw(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:50])
        s = s.replace(a, b, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


rw("vps/harness.py", [
    ("        preds, lat, inl, infos = [], [], [], []\n",
     "        preds, lat, inl, infos = [], [], [], []\n"
     "        sigma = float(os.environ.get(\"PRIOR_SIGMA\", 0))  # m; >0 gives uses_prior methods a noisy position prior (GT + N(0, sigma^2) in xy) per query\n"
     "        prng = np.random.default_rng(seed + 12345)\n"),
    ("            T, info = M.localize(img, q[\"K\"])\n",
     "            kw = {\"prior_xy\": q[\"T\"][len(preds)][:2, 3] + prng.normal(0, sigma, 2)} if sigma > 0 and getattr(M, \"uses_prior\", False) else {}\n"
     "            T, info = M.localize(img, q[\"K\"], **kw)\n"),
])
rw("vps/m1lf.py", [
    ("class Method(m1l.Method):\n    def prepare(self, map_dir):",
     "PRIOR_R = float(os.environ.get(\"M1LF_PRIOR_R\", 20))  # m, candidate radius around the prior when one is given\n\n\nclass Method(m1l.Method):\n    uses_prior = True\n\n    def prepare(self, map_dir):"),
    ("        self.gs = torch.cat(self.gs)\n        self.desc =", "        self.pv = np.array([T[:3, 3] for T in self.RT])\n        self.gs = torch.cat(self.gs)\n        self.desc ="),
    ("    def localize(self, img, K):\n        q = m1l.gray_t(img)\n        n = len(self.g)\n        pool = list(range(n))\n        if self.desc is not None:",
     "    def localize(self, img, K, prior_xy=None):\n        q = m1l.gray_t(img)\n        n = len(self.g)\n        pool = list(range(n))\n        if prior_xy is not None:  # only views near the prior are candidates (a tile-streaming robot would only have those loaded)\n            near = np.where(np.linalg.norm(self.pv[:, :2] - prior_xy, axis=1) < PRIOR_R)[0]\n            if len(near):\n                sub = near\n                if self.desc is not None:\n                    sim = mega_embed(self.mega, [img]) @ self.desc[torch.as_tensor(near, device=self.desc.device)].T\n                    sub = near[torch.topk(sim[0], min(SHORT, len(near))).indices.cpu().numpy()]\n                pool = sub.tolist()\n                self._finish = True\n        if prior_xy is None and self.desc is not None:"),
])
print("patched")
