"""Planar Monte Carlo localization (x, y, heading of the robot base), the online version of scripts/mcl_test.py (same model and settings).
Predict with odometry increments (base frame), update with a PnP pose (robust likelihood: (1-EPS) N + EPS*floor), resample when the effective sample size drops,
re-seed a fraction INJ of the lowest-weight particles around the observation (recovery). spread() = weighted RMS distance to the mean = the confidence gate."""
import numpy as np


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class MCL:
    def __init__(self, xy, heading, sigma_xy=5.0, sigma_deg=10.0, n=500, eps=0.5, sxy=1.5, syaw_deg=1.5, inj=0.1, odo_t=0.01, odo_r_deg=0.1, seed=0):
        self.rng = np.random.default_rng(seed)
        self.n, self.eps, self.sxy, self.syaw, self.inj = n, eps, sxy, np.radians(syaw_deg), inj
        self.odo_t, self.odo_r = odo_t, odo_r_deg
        self.p = np.c_[xy[0] + self.rng.normal(0, sigma_xy, n), xy[1] + self.rng.normal(0, sigma_xy, n), heading + np.radians(self.rng.normal(0, sigma_deg, n))]
        self.w = np.full(n, 1.0 / n)

    def predict(self, rel_xy, dpsi):
        """rel_xy: (forward, left) motion in the previous base frame (m); dpsi: heading change (rad). Odometry noise is added per particle."""
        dist = float(np.hypot(*rel_xy))
        r = np.asarray(rel_xy)[None] + self.rng.normal(0, self.odo_t * dist + 0.01, (self.n, 2))
        d = dpsi + np.radians(self.rng.normal(0, self.odo_r * dist + 0.2, self.n))
        c, s = np.cos(self.p[:, 2]), np.sin(self.p[:, 2])
        self.p[:, 0] += c * r[:, 0] - s * r[:, 1]
        self.p[:, 1] += s * r[:, 0] + c * r[:, 1]
        self.p[:, 2] = wrap(self.p[:, 2] + d)

    def update(self, obs, inl, gate_m=15.0, confident=3.0):
        """obs = (x, y, heading) of the base from a PnP pose with `inl` inliers. Returns False when the observation is rejected: while the filter is confident
        (spread < `confident` m) a pose farther than `gate_m` from its mean is an aliasing outlier, not information (and must not seed injected particles)."""
        if self.spread() < confident and np.linalg.norm(self.mean()[:2] - obs[:2]) > gate_m:
            return False
        sxy = self.sxy * np.clip((80.0 / max(inl, 12)) ** 0.5, 0.7, 3.0)
        dxy = np.linalg.norm(self.p[:, :2] - obs[:2], axis=1)
        dya = wrap(self.p[:, 2] - obs[2])
        lik = np.exp(-0.5 * (dxy / sxy) ** 2 - 0.5 * (dya / self.syaw) ** 2)
        self.w = self.w * ((1 - self.eps) * lik + self.eps * 1e-4)
        self.w /= self.w.sum()
        if 1.0 / np.sum(self.w ** 2) < self.n / 2:
            idx = self.rng.choice(self.n, self.n, p=self.w)
            self.p, self.w = self.p[idx], np.full(self.n, 1.0 / self.n)
        if self.inj > 0 and inl >= 40:
            k = int(self.inj * self.n)
            j = np.argsort(self.w)[:k]
            self.p[j] = np.c_[obs[:2] + self.rng.normal(0, 1.0, (k, 2)), obs[2] + np.radians(self.rng.normal(0, 3, k))]
            self.w[j] = self.w.mean()
            self.w /= self.w.sum()
        return True

    def mean(self):
        xy = np.average(self.p[:, :2], axis=0, weights=self.w)
        h = np.arctan2(np.average(np.sin(self.p[:, 2]), weights=self.w), np.average(np.cos(self.p[:, 2]), weights=self.w))
        return np.array([xy[0], xy[1], h])

    def spread(self):
        m = self.mean()
        return float(np.sqrt(np.average(np.sum((self.p[:, :2] - m[:2]) ** 2, axis=1), weights=self.w)))

    def snapshot(self):
        return self.p.copy(), self.w.copy()

    def restore(self, snap):
        self.p, self.w = snap[0].copy(), snap[1].copy()
