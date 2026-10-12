"""One-off patch (repo root): gravity-aided pose refinement. A robot's IMU gives the gravity direction in the camera frame to ~0.1 deg, which fixes pitch and roll; only yaw and position (4 DoF) are then solved,
minimising the (Huber) reprojection error of the RANSAC inliers, starting from the PnP pose. Simulated IMU: GT gravity direction + rotation noise N(0, GRAV_SIGMA_DEG^2) per axis. Enabled by GRAV_SIGMA_DEG > 0 in the harness."""
import io


def rw(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:60])
        s = s.replace(a, b, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


GRAV = '''

def grav_refine(p3, p2, K, Tc0, g_c):
    """Tc0: camera-to-world 4x4 from PnP; g_c: unit gravity direction in the CAMERA frame (down). Returns camera-to-world with pitch/roll fixed by g_c; free: yaw psi and camera centre."""
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation as Rot
    u = -np.asarray(g_c, float) / np.linalg.norm(g_c)  # camera-frame 'up'
    z = np.array([0.0, 0.0, 1.0])
    ax = np.cross(u, z)
    s = np.linalg.norm(ax)
    Rmin = np.eye(3) if s < 1e-9 else Rot.from_rotvec(ax / s * np.arctan2(s, u @ z)).as_matrix()  # minimal rotation taking u to world up
    M = Tc0[:3, :3] @ Rmin.T
    psi0 = np.arctan2(M[1, 0], M[0, 0])

    def res(x):
        c, sn = np.cos(x[0]), np.sin(x[0])
        R = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ Rmin  # R u = z for every yaw
        Xc = (p3 - x[1:4]) @ R  # world -> camera: R^T (X - t)
        return (np.c_[K[0, 0] * Xc[:, 0] / Xc[:, 2] + K[0, 2], K[1, 1] * Xc[:, 1] / Xc[:, 2] + K[1, 2]] - p2).ravel()

    sol = least_squares(res, np.r_[psi0, Tc0[:3, 3]], loss="huber", f_scale=2.0, max_nfev=50)
    c, sn = np.cos(sol.x[0]), np.sin(sol.x[0])
    T = np.eye(4)
    T[:3, :3] = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]]) @ Rmin
    T[:3, 3] = sol.x[1:4]
    return T
'''

rw("vps/m1l.py", [
    ("class Method:", GRAV.lstrip("\n") + "\n\nclass Method:"),
    ("    def _pose(self, res, K, views=None):", "    def _pose(self, res, K, views=None, grav_c=None):"),
    ("        Tc = np.linalg.inv(T)\n        proj, _ = cv2.projectPoints(p3[i], rv, tv, K, None)",
     "        Tc = np.linalg.inv(T)\n        if grav_c is not None and len(i) >= 12:  # gravity-aided: pitch/roll from the IMU, solve yaw + position\n            Tc = grav_refine(p3[i], p2[i], K, Tc, grav_c)\n            T = np.linalg.inv(Tc)\n            R = T[:3, :3]\n            tv = T[:3, 3:4]\n            rv, _ = cv2.Rodrigues(R)\n        proj, _ = cv2.projectPoints(p3[i], rv, tv, K, None)"),
])
rw("vps/m1lf.py", [
    ("    def localize(self, img, K, prior_xy=None):", "    def localize(self, img, K, prior_xy=None, grav_c=None):"),
    ("        T, info = self._pose(res, K)\n", "        T, info = self._pose(res, K, grav_c=grav_c)\n"),
    ("views=([ids_r], [T]))", "views=([ids_r], [T]), grav_c=grav_c)"),
])
rw("vps/harness.py", [
    ("        prng = np.random.default_rng(seed + 12345)\n",
     "        prng = np.random.default_rng(seed + 12345)\n        gsig = float(os.environ.get(\"GRAV_SIGMA_DEG\", 0))  # deg; >0 simulates an IMU gravity direction (GT + rotation noise) handed to gravity-aware methods\n"),
    ("            T, info = M.localize(img, q[\"K\"], **kw)\n",
     "            if gsig > 0 and getattr(M, \"uses_prior\", False):\n                from scipy.spatial.transform import Rotation as _R\n                Rg = q[\"T\"][len(preds)][:3, :3]\n                kw[\"grav_c\"] = (_R.from_rotvec(np.radians(prng.normal(0, gsig, 3))).as_matrix() @ Rg.T @ np.array([0.0, 0.0, -1.0]))\n            T, info = M.localize(img, q[\"K\"], **kw)\n"),
])
print("patched")
