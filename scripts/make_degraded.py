"""Sensor-degradation test set: the 285 route-2 query images (ug2s) degraded in 7 ways, concatenated into ONE session (variants stacked) so the evaluation loads the map once.
Variants: clean | noise (Gaussian sigma 10) | motion blur (15 px, random direction) | dark (gamma 2.2 x 0.7) | bright (gamma 0.5 x 1.2) | colour cast (R x0.8, B x1.2) | barrel distortion (k1 = -0.10, uncorrected) | JPEG q=25.
Per-query rows of the result are in session order, so stats per variant = slices of 285. usage: make_degraded.py OUT_SESSION"""
import os, shutil, sys
import cv2, numpy as np
SRC = "/root/data/ug2s_img"; OUT = sys.argv[1]
rng = np.random.default_rng(0)
names = sorted(os.listdir(SRC + "/images")); T = np.load(SRC + "/poses.npy"); K = np.load(SRC + "/K.npy")
def noise(im): return np.clip(im.astype(np.float32) + rng.normal(0, 10, im.shape), 0, 255).astype(np.uint8)
def blur(im):
    L = 15; k = np.zeros((L, L), np.float32); k[L // 2, :] = 1; M = cv2.getRotationMatrix2D((L / 2 - .5, L / 2 - .5), rng.uniform(0, 180), 1); k = cv2.warpAffine(k, M, (L, L)); k /= max(k.sum(), 1e-6)
    return cv2.filter2D(im, -1, k)
def gamma(g, gain): return lambda im: np.clip(255 * gain * (im / 255.0) ** g, 0, 255).astype(np.uint8)
def cast(im): f = np.array([1.2, 1.0, 0.8], np.float32); return np.clip(im * f, 0, 255).astype(np.uint8)  # BGR: B x1.2, R x0.8
def barrel(im):
    h, w = im.shape[:2]; fx = K[0, 0]; cx, cy = K[0, 2], K[1, 2]
    u, v = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)); x, y = (u - cx) / fx, (v - cy) / fx; r2 = x * x + y * y
    # distorted image sampled so that straight lines bow outwards by k1 = -0.10: source = undistorted coords scaled by (1 + k1 r^2)
    s = 1 - 0.10 * r2; return cv2.remap(im, (x * s * fx + cx).astype(np.float32), (y * s * fx + cy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
def jpeg(im): return cv2.imdecode(cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 25])[1], 1)
V = [("clean", lambda im: im), ("noise", noise), ("blur", blur), ("dark", gamma(2.2, .7)), ("bright", gamma(.5, 1.2)), ("cast", cast), ("barrel", barrel), ("jpeg", jpeg)]
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + "/images"); idx = 0
for vn, fn in V:
    for n, Ti in zip(names, T):
        cv2.imwrite(f"{OUT}/images/{idx:05d}.png", fn(cv2.imread(f"{SRC}/images/{n}"))); idx += 1
np.save(OUT + "/poses.npy", np.concatenate([T] * len(V))); shutil.copy(SRC + "/K.npy", OUT + "/K.npy")
print("variants:", [v[0] for v in V], "queries per variant:", len(names), "total", idx)
