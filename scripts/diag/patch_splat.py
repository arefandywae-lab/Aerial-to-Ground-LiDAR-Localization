"""One-off patch (repo root): splat radius in metres and its pixel cap become env-tunable (M1_SPLAT, M1_RMAX). Defaults reproduce all earlier results (0.03 m, 4 px)."""
import io


def rw(path, pairs):
    s = io.open(path, encoding="utf-8").read()
    for a, b in pairs:
        assert a in s, (path, a[:40])
        s = s.replace(a, b)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)


rw("vps/m1.py", [("SPLAT_M = 0.03  # world radius of a map point in the render; sets hole filling vs. blur",
                  'SPLAT_M = float(os.environ.get("M1_SPLAT", 0.03))  # world radius of a map point in the render; sets hole filling vs. blur (0.03 for a 0.1 m map, ~0.12 for a 0.25 m voxel map)')])
rw("vps/m1lf.py", [("from m1 import FILL_PX, SPLAT_M, ZFAR, shade  # noqa: F401  (FILL_PX re-exported for tuning scripts)",
                    "from m1 import FILL_PX, SPLAT_M, ZFAR, shade  # noqa: F401  (FILL_PX re-exported for tuning scripts)\n\nRMAX = int(os.environ.get(\"M1_RMAX\", 4))  # max splat radius in pixels (cost grows with (2*RMAX+1)^2)"),
                   ("r = torch.clamp(torch.round(fx * SPLAT_M / zv), 0, 4).long()", "r = torch.clamp(torch.round(fx * SPLAT_M / zv), 0, RMAX).long()"),
                   ("    for du in range(-4, 5):\n        for dv in range(-4, 5):", "    for du in range(-RMAX, RMAX + 1):\n        for dv in range(-RMAX, RMAX + 1):")])
print("patched")
