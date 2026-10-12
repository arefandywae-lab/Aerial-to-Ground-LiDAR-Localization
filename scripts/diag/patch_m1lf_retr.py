"""One-off patch (run from repo root): m1lf gets (a) lean storage of render images, (b) MegaLoc vector retrieval shortlist, (c) M1_VIEWS (explicit virtual viewpoints)."""
import io

p = "vps/m1lf.py"
s = io.open(p, encoding="utf-8").read()
a = s.index("class Method(m1l.Method):")
head = s[:a]
head = head.replace('YAWS = [float(v)', '''RETR = os.environ.get("M1LF_RETR", "none")  # none | megaloc: vector shortlist before the LoFTR stages
SHORT = int(os.environ.get("M1LF_K", 50))  # shortlist size
VIEWS = os.environ.get("M1_VIEWS", "")  # .npy of (N,4,4) camera-to-world virtual viewpoints (vps/viewpoints.py); overrides STEP/YAWS
YAWS = [float(v)''', 1)
head = head.replace("import cv2\n", "import cv2\n", 1)
tail = '''MEAN = STD = None


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


class Method(m1l.Method):
    def prepare(self, map_dir):
        s = load_session(map_dir)
        self.K = s["K"]
        d = np.load(m1l.LIDAR_MAP)
        self.P = d["pts"].astype(np.float64)
        rgb = d["rgb"]
        Pg = torch.from_numpy(d["pts"]).float().to(m1l.DEV)
        self.loftr = LoFTR(pretrained="outdoor").to(m1l.DEV).eval()
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
        for T in views:
            img, ids = shade(render_gpu(Pg, T, self.K), rgb)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            self.g.append(torch.from_numpy(gray)[None, None])  # uint8 on the CPU: identical values to gray/255 after .float()/255, 4x smaller, off the GPU
            self.gs.append(F.interpolate(m1l.gray_t(img), size=(240, 320), mode="bilinear", antialias=True))
            self.ids.append(ids)
            if RETR == "megaloc":
                buf.append(img)
                if len(buf) == 32:
                    desc.append(mega_embed(self.mega, buf)), buf.clear()
        if buf:
            desc.append(mega_embed(self.mega, buf))
        self.gs = torch.cat(self.gs)
        self.desc = torch.cat(desc) if desc else None
        print(f"M1LF map: {len(self.g)} renders, {len(self.P)} map points, fp16={FP16} coarse={COARSE} topn={TOPN} retr={RETR} k={SHORT} "
              f"views={'file' if VIEWS else f'yaws={YAWS} step={m1l.STEP}'}")

    def _g(self, i):
        return self.g[i].to(m1l.DEV).float().div(255)

    def _match(self, a, b):
        with torch.autocast("cuda", dtype=torch.float16, enabled=bool(FP16)):
            return self.loftr({"image0": a, "image1": b})

    @torch.no_grad()
    def localize(self, img, K):
        q = m1l.gray_t(img)
        n = len(self.g)
        pool = list(range(n))
        if self.desc is not None:  # vector retrieval: cosine similarity against every render descriptor, keep the top SHORT
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
        for i in cand:
            o = self._match(q, self._g(i))
            ok = o["confidence"] > m1l.CONF
            res.append((int(ok.sum()), i, o["keypoints0"][ok].float().cpu().numpy(), o["keypoints1"][ok].float().cpu().numpy()))
        return self._pose(res, K)
'''
io.open(p, "w", encoding="utf-8", newline="\n").write(head + tail)
print("patched")
