#!/usr/bin/env python3
"""VPS wrapper + evaluation harness (components 4 and 5).

A method is a class with  prepare(map_dir)  and  localize(img_bgr, K) -> (T_cam_to_world 4x4 | None, info dict).
Same query set for every method; GT from Gazebo. Success thresholds are fixed up front (Aachen-style):
    (0.25 m, 2 deg), (0.5 m, 5 deg), (5 m, 10 deg)      # to be confirmed after experiment 1 (spec sec. 5)

usage: harness.py --method m0 --map /root/data/s0_img --queries /root/data/q1_img --out results/m0_q1.json
"""
import argparse
import importlib
import json
import os
import subprocess
import threading
import time

import cv2
import numpy as np

THRESH = [(0.25, 2.0), (0.5, 5.0), (5.0, 10.0)]


def load_session(d):
    return dict(images=sorted(os.path.join(d, "images", f) for f in os.listdir(f"{d}/images")),
                T=np.load(f"{d}/poses.npy"), K=np.load(f"{d}/K.npy"))


def pose_err(T, G):
    dt = np.linalg.norm(T[:3, 3] - G[:3, 3])
    c = (np.trace(T[:3, :3].T @ G[:3, :3]) - 1) / 2
    return dt, np.degrees(np.arccos(np.clip(c, -1, 1)))


def metrics(preds, gts):
    """preds: list of 4x4 or None."""
    e = np.array([pose_err(p, g) if p is not None else (np.inf, np.inf) for p, g in zip(preds, gts)])
    ok = np.isfinite(e[:, 0])
    m = {"n": len(e), "localized": float(ok.mean()),
         "median_t_m": float(np.median(e[ok, 0])) if ok.any() else None,
         "median_r_deg": float(np.median(e[ok, 1])) if ok.any() else None}
    for t, r in THRESH:
        m[f"recall@{t}m,{r}deg"] = float(((e[:, 0] <= t) & (e[:, 1] <= r)).mean())
    return m, e


class VramPeak:
    """Peak GPU memory of THIS process (MiB) via torch.cuda; falls back to 0 for CPU-only runs.
    Device-wide nvidia-smi sampling was replaced after audit: it included other GPU apps."""
    def __enter__(self):
        try:
            import torch
            self.t = torch
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()
                self.ok = True
                return self
        except Exception:
            pass
        self.ok = False
        return self

    @property
    def peak(self):
        return int(self.t.cuda.max_memory_allocated() / 1024 / 1024) if self.ok else 0

    base = 0

    def __exit__(self, *a):
        pass


def run(method, map_dir, query_dir, out=None, seed=0):
    cv2.setRNGSeed(seed)  # cv2.solvePnPRansac uses this; without it, numbers change per run
    mod = importlib.import_module(method)
    M = mod.Method()
    t0 = time.perf_counter()
    with VramPeak() as vm:
        M.prepare(map_dir)
        prep_s = time.perf_counter() - t0
        q = load_session(query_dir)
        # warm-up (CUDA/cuDNN autotune, allocator) so it doesn't inflate p95/p99; reseed after so RANSAC state matches a run without it
        for _ in range(2):
            M.localize(cv2.imread(q["images"][0]), q["K"])
        cv2.setRNGSeed(seed)
        preds, lat, inl, infos = [], [], [], []
        sigma = float(os.environ.get("PRIOR_SIGMA", 0))  # m; >0 gives uses_prior methods a noisy position prior (GT + N(0, sigma^2) in xy) per query
        prng = np.random.default_rng(seed + 12345)
        gsig = float(os.environ.get("GRAV_SIGMA_DEG", 0))  # deg; >0 simulates an IMU gravity direction (GT + rotation noise) handed to gravity-aware methods
        for p in q["images"]:
            img = cv2.imread(p)
            t = time.perf_counter()
            kw = {"prior_xy": q["T"][len(preds)][:2, 3] + prng.normal(0, sigma, 2)} if sigma > 0 and getattr(M, "uses_prior", False) else {}
            if gsig > 0 and getattr(M, "uses_prior", False):
                from scipy.spatial.transform import Rotation as _R
                Rg = q["T"][len(preds)][:3, :3]
                kw["grav_c"] = (_R.from_rotvec(np.radians(prng.normal(0, gsig, 3))).as_matrix() @ Rg.T @ np.array([0.0, 0.0, -1.0]))
            T, info = M.localize(img, q["K"], **kw)
            lat.append(time.perf_counter() - t)
            preds.append(T)
            inl.append(info.get("inliers", 0))
            infos.append(info)
    m, e = metrics(preds, q["T"])
    lat_ms = 1e3 * np.array(lat)
    m.update(method=method, map=map_dir, queries=query_dir, seed=seed, prepare_s=prep_s,
             latency_ms_p50=float(np.percentile(lat_ms, 50)),
             latency_ms_p95=float(np.percentile(lat_ms, 95)),
             latency_ms_p99=float(np.percentile(lat_ms, 99)),
             vram_peak_mib_process=vm.peak)
    # precision@recall gates by inlier count: ratio of CORRECT (<=5m,10deg) over RETURNED at each inlier threshold
    inl_a, dt, dr = np.array(inl), e[:, 0], e[:, 1]
    for gate in (12, 20, 40, 80):
        ret = inl_a >= gate
        correct = ret & (dt <= 5.0) & (dr <= 10.0)
        m[f"gate{gate}_returned"] = float(ret.mean())
        m[f"gate{gate}_precision"] = float(correct.sum() / ret.sum()) if ret.any() else None
    print(json.dumps(m, indent=1))
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(m, open(out, "w"), indent=1)
        np.save(out.replace(".json", "_err.npy"), np.c_[e, inl_a])  # dt, dr, inliers per query
        np.save(out.replace(".json", "_pred.npy"), np.array([p if p is not None else np.full((4, 4), np.nan) for p in preds]))  # estimated camera-to-world poses (NaN = none)
        names = sorted({k for i in infos for k in i} - {"inliers"})
        if names:  # per-query confidence features (NaN where the method returned no pose / has no such feature)
            np.save(out.replace(".json", "_feat.npy"), np.array([[i.get(k, np.nan) for k in names] for i in infos], float))
            json.dump({"feature_names": names}, open(out.replace(".json", "_feat_names.json"), "w"))
    return m


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--method", required=True)
    a.add_argument("--map", required=True)
    a.add_argument("--queries", required=True)
    a.add_argument("--out")
    a.add_argument("--seed", type=int, default=0)
    o = a.parse_args()
    run(o.method, o.map, o.queries, o.out, o.seed)
