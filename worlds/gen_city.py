#!/usr/bin/env python3
"""Random 200 x 200 m worlds of several styles for the generalisation series (same drone / ground robot / sensors as gen_urban.py).

styles
  grid      3x3 streets, 4x4 blocks split into lots (the original urban world, new seed -> new layout, heights, textures)
  oldtown   irregular binary-space-partition blocks separated by 3-8 m lanes and alleys, 6-22 m buildings
  suburb    low houses (4-7 m) set back from a road grid, thin walls (fences) and tree-like green boxes, large open gaps
  bridge    grid city with an elevated road deck (bridge, z 6-7 m, over a cross street) and a roofed tunnel (walls + roof) along one street
  canyon    grid with very tall (30-60 m) buildings and narrow 6 m streets

Also writes WORLD.json: ground-robot waypoints (a random walk over the free space on an occupancy grid, simplified) and drone lanes above everything.
usage: gen_city.py --style oldtown --seed 3 --out /root/worlds/oldtown3.sdf
"""
import argparse
import json
import os
import random
import sys
from collections import deque

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_world as gw  # noqa: E402
import gen_urban as gu  # noqa: E402

SIZE = 200.0
NFAC = 4


def slab(name, x, y, z0, sx, sy, sz, kind="box", rgb=(.55, .55, .55)):
    """box whose bottom is at z0 (bridge deck, tunnel roof)"""
    return (f'\n    <model name="{name}"><static>true</static><pose>{x:.2f} {y:.2f} {z0 + sz / 2:.2f} 0 0 0</pose><link name="l">'
            f'<collision name="c"><geometry><box><size>{sx:.2f} {sy:.2f} {sz:.2f}</size></box></geometry></collision>'
            f'<visual name="v"><geometry><box><size>{sx:.2f} {sy:.2f} {sz:.2f}</size></box></geometry>{gw.material(rgb, kind)}</visual></link></model>')


def split(rng, x0, y0, x1, y1, lane, minsz, out, depth=0):
    """binary space partition; leaves are lots, `lane` metres are left between the two halves"""
    w, h = x1 - x0, y1 - y0
    if (w < 2 * minsz and h < 2 * minsz) or (depth > 1 and rng.random() < .25):
        out.append((x0, y0, x1, y1))
        return
    vertical = w > h if abs(w - h) > 8 else rng.random() < .5
    if vertical and w >= 2 * minsz + lane:
        c = rng.uniform(x0 + minsz, x1 - minsz - lane)
        split(rng, x0, y0, c, y1, lane, minsz, out, depth + 1)
        split(rng, c + lane, y0, x1, y1, lane, minsz, out, depth + 1)
    elif h >= 2 * minsz + lane:
        c = rng.uniform(y0 + minsz, y1 - minsz - lane)
        split(rng, x0, y0, x1, c, lane, minsz, out, depth + 1)
        split(rng, x0, c + lane, x1, y1, lane, minsz, out, depth + 1)
    else:
        out.append((x0, y0, x1, y1))


def layout(style, rng):
    """-> list of (name, kind, x, y, z0, sx, sy, sz) boxes"""
    B = []
    fac = lambda: f"fac{rng.randrange(NFAC)}"
    h0 = SIZE / 2 - 4
    if style in ("grid", "bridge", "canyon"):
        street = 6.0 if style == "canyon" else 10.0
        cs = [-50, 0, 50]
        edges = [-h0] + [c for c in cs for c in (c - street / 2, c + street / 2)] + [h0]
        spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
        for (xa, xb) in spans:
            for (ya, yb) in spans:
                for i, (a, b, c, d) in enumerate(gu_lots(rng, xa, xb, ya, yb)):
                    hgt = rng.uniform(30, 60) if style == "canyon" else (rng.choice([4, 6, 8]) if rng.random() < .25 else rng.uniform(10, 35))
                    B.append((f"b{len(B)}", fac(), (a + b) / 2, (c + d) / 2, 0, b - a, d - c, hgt))
        if style == "bridge":
            # bridge: deck over the cross street x=0 at y in [-100+8, 100-8] is the street itself -> deck spans the street crossing y=0 street, z 6-7 m, with two piers
            B.append(("deck", "box", 0, 0, 6.0, 10.0, 56.0, 1.0))
            B.append(("pier0", "box", 0, -26, 0, 3.0, 2.0, 6.0))
            B.append(("pier1", "box", 0, 26, 0, 3.0, 2.0, 6.0))
            # tunnel along street y=-50 from x=-70 to x=-30: two walls + roof
            B.append(("tw0", fac(), -50, -55.5, 0, 40, 1.0, 6.0))
            B.append(("tw1", fac(), -50, -44.5, 0, 40, 1.0, 6.0))
            B.append(("troof", "box", -50, -50, 6.0, 40, 12.0, 1.0))
    elif style == "oldtown":
        lots = []
        # lanes of 3-8 m between lots
        stack = [(-h0, -h0, h0, h0, 0)]
        while stack:
            x0, y0, x1, y1, d = stack.pop()
            w, h = x1 - x0, y1 - y0
            lane = rng.uniform(3, 8)
            if (w < 36 and h < 36) or (d >= 4 and rng.random() < .3):
                lots.append((x0, y0, x1, y1))
                continue
            if (w >= h and w >= 20 + lane) or h < 20 + lane:
                c = rng.uniform(x0 + 10, x1 - 10 - lane)
                stack += [(x0, y0, c, y1, d + 1), (c + lane, y0, x1, y1, d + 1)]
            else:
                c = rng.uniform(y0 + 10, y1 - 10 - lane)
                stack += [(x0, y0, x1, c, d + 1), (x0, c + lane, x1, y1, d + 1)]
        for (x0, y0, x1, y1) in lots:
            B.append((f"b{len(B)}", fac(), (x0 + x1) / 2, (y0 + y1) / 2, 0, x1 - x0, y1 - y0, rng.uniform(6, 22)))
    elif style == "suburb":
        for rx in range(-90, 91, 30):  # road grid every 30 m (roads 8 m wide); houses in the cells, set back from the roads
            for ry in range(-90, 91, 30):
                cx, cy = rx + 15, ry + 15
                if abs(cx) > 90 or abs(cy) > 90:
                    continue
                for k in range(rng.randint(2, 4)):
                    sx, sy = rng.uniform(6, 10), rng.uniform(7, 12)
                    x = cx + rng.uniform(-15 + 4 + sx / 2, 15 - 4 - sx / 2)
                    y = cy + rng.uniform(-15 + 4 + sy / 2, 15 - 4 - sy / 2)
                    if any(abs(x - b[2]) < (sx + b[5]) / 2 + 1 and abs(y - b[3]) < (sy + b[6]) / 2 + 1 for b in B if b[1].startswith("fac")):
                        continue
                    B.append((f"h{len(B)}", fac(), x, y, 0, sx, sy, rng.uniform(4, 7)))
                if rng.random() < .6:  # fence
                    B.append((f"f{len(B)}", "box", cx + rng.uniform(-10, 10), cy + rng.choice([-12.5, 12.5]), 0, rng.uniform(8, 16), .2, 1.5))
                for _ in range(rng.randint(1, 3)):  # trees as green boxes
                    B.append((f"t{len(B)}", "tree", cx + rng.uniform(-12, 12), cy + rng.uniform(-12, 12), 0, 2.5, 2.5, rng.uniform(4, 8)))
    return B


def gu_lots(rng, xa, xb, ya, yb):
    """1-4 lots inside a block [xa,xb] x [ya,yb] separated by 3 m alleys -> (x0, x1, y0, y1) lists"""
    def cuts(a, b):
        if rng.random() < .25:
            return [(a, b)]
        m = rng.uniform(-6, 6) + (a + b) / 2
        return [(a, m - 1.5), (m + 1.5, b)]
    return [(c0, c1, d0, d1) for c0, c1 in cuts(xa, xb) for d0, d1 in cuts(ya, yb)]


def free_grid(B, res=1.0, clear=1.6):
    n = int(SIZE / res)
    occ = np.zeros((n, n), bool)
    for _, _, x, y, z0, sx, sy, sz in B:
        if z0 > 2.0 and z0 + sz > 0 and sz < 3:  # elevated deck / roof slab: ground below is free
            continue
        if z0 == 0 or z0 < 2:
            x0, x1 = int((x - sx / 2 - clear + SIZE / 2) / res), int((x + sx / 2 + clear + SIZE / 2) / res) + 1
            y0, y1 = int((y - sy / 2 - clear + SIZE / 2) / res), int((y + sy / 2 + clear + SIZE / 2) / res) + 1
            occ[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
    occ[:int(clear), :] = occ[-int(clear):, :] = occ[:, :int(clear)] = occ[:, -int(clear):] = True
    return ~occ


def rdp(P, eps):
    """Ramer-Douglas-Peucker polyline simplification (iterative)"""
    keep = np.zeros(len(P), bool); keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ab = P[b] - P[a]; n = np.hypot(*ab)
        d = np.abs(ab[0] * (P[a + 1:b, 1] - P[a, 1]) - ab[1] * (P[a + 1:b, 0] - P[a, 0])) / n if n > 0 else np.hypot(*(P[a + 1:b] - P[a]).T)
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[a + 1 + k] = True; stack += [(a, a + 1 + k), (a + 1 + k, b)]
    return P[keep]


def plan(free, rng, length=450.0, res=1.0):
    """random walk over free space: pick far waypoints, connect by BFS shortest paths, simplify"""
    n = free.shape[0]
    lab = np.zeros(free.shape, int)
    k = 0
    for sy, sx in zip(*np.where(free)):  # largest connected component
        if lab[sy, sx]:
            continue
        k += 1
        q = deque([(sy, sx)]); lab[sy, sx] = k
        while q:
            y, x = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < n and 0 <= xx < n and free[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = k; q.append((yy, xx))
    big = np.bincount(lab[lab > 0]).argmax()
    cells = np.argwhere(lab == big)
    cur = tuple(cells[rng.randrange(len(cells))])
    path, total = [cur], 0.0
    for _ in range(40):
        goal = tuple(cells[rng.randrange(len(cells))])
        if np.hypot(goal[0] - cur[0], goal[1] - cur[1]) < 40:
            continue
        prev = {cur: None}; q = deque([cur])
        while q and goal not in prev:
            y, x = q.popleft()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = (y + dy, x + dx)
                if 0 <= nb[0] < n and 0 <= nb[1] < n and lab[nb] == big and nb not in prev:
                    prev[nb] = (y, x); q.append(nb)
        seg = []
        c = goal
        while c is not None:
            seg.append(c); c = prev[c]
        seg = seg[::-1][1:]
        path += seg; total += len(seg) * res; cur = goal
        if total >= length:
            break
    pts = [(c[1] * res - SIZE / 2 + res / 2, c[0] * res - SIZE / 2 + res / 2) for c in path]
    out = rdp(np.array(pts), 1.0)  # Ramer-Douglas-Peucker, 1 m: corner cutting stays inside the 1.6 m clearance; far fewer waypoints (the driver slows at every one)
    return [tuple(p) for p in out], total


def build(style, seed, sun=1.0):
    rng = random.Random(seed * 101 + sum(map(ord, style)))
    B = layout(style, rng)
    parts = []
    for name, kind, x, y, z0, sx, sy, sz in B:
        name = "b" + name  # the layout preview matches model names starting with b
        if kind == "tree":
            parts.append(slab(name, x, y, z0, sx, sy, sz, "tree", (.15, .45, .15)))
        elif z0 == 0:
            parts.append(gw.box(name, x, y, sx, sy, sz, (.6, .6, .6), kind))
        else:
            parts.append(slab(name, x, y, z0, sx, sy, sz, kind))
    free = free_grid(B)
    wp, length = plan(free, rng)
    hmax = max(b[4] + b[7] for b in B)
    zf = max(30.0, hmax + 12.0)  # fly low enough that the LiDAR sees structure (at 45 m over 6-22 m buildings FAST-LIO degenerated: ATE 5 m)
    lanes = []
    ys = list(np.arange(-85, 86, 45.0))
    for i, y in enumerate(ys):
        lanes += [(-85 if i % 2 == 0 else 85, y, zf), (85 if i % 2 == 0 else -85, y, zf)]
    robot = gw.ROBOT.replace("<pose>-12 -8 0.15 0 0 0</pose>", f"<pose>{wp[0][0]:.2f} {wp[0][1]:.2f} 0.15 0 0 0</pose>")
    sdf = gw.build(seed, sun, 0)
    head = sdf[:sdf.index('<model name="ground">')].replace('world name="room"', f'world name="{style}"')
    plane = f"<plane><normal>0 0 1</normal><size>{SIZE} {SIZE}</size></plane>"
    ground = (f'<model name="ground"><static>true</static><link name="l"><collision name="c"><geometry>{plane}</geometry></collision>'
              f'<visual name="v"><geometry>{plane}</geometry>{gw.material((.35, .35, .35), "road")}</visual></link></model>')
    drone = gu.DRONE.replace("<pose>-90 -90 40 0 0 0</pose>", f"<pose>-90 -90 {zf:.0f} 0 0 0</pose>")
    sdf = head + ground + "".join(parts) + robot + drone + "\n  </world>\n</sdf>\n"
    return sdf, dict(style=style, seed=seed, ground=wp, ground_len=length, drone=lanes, zf=zf, n_boxes=len(B), hmax=hmax)


def make_road_plain(path, seed, n=2048):
    r = np.random.default_rng(seed)
    img = cv2.resize(r.random((64, 64), np.float32) * .15 + .3, (n, n))[..., None] * np.ones((1, 1, 3), np.float32)
    cv2.imwrite(path, np.clip(img * 255, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--style", default="grid", choices=["grid", "oldtown", "suburb", "bridge", "canyon"])
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--out", required=True)
    o = a.parse_args()
    d = os.path.dirname(os.path.abspath(o.out))
    base = os.path.splitext(os.path.basename(o.out))[0]
    for k in range(NFAC):
        gw.TEX[f"fac{k}"] = f"{d}/{base}_fac{k}.png"
        gu.make_facade(gw.TEX[f"fac{k}"], 1000 * o.seed + 10 * len(o.style) + k)
    gw.TEX["road"] = f"{d}/{base}_road.png"
    make_road_plain(gw.TEX["road"], o.seed)
    sdf, meta = build(o.style, o.seed)
    open(o.out, "w").write(sdf)
    json.dump(meta, open(o.out.replace(".sdf", ".json"), "w"))
    gu.preview(o.out)
    print(f"{o.out}: style {o.style}, {meta['n_boxes']} boxes, hmax {meta['hmax']:.0f} m, ground route {meta['ground_len']:.0f} m / {len(meta['ground'])} waypoints, drone z {meta['zf']:.0f}")
