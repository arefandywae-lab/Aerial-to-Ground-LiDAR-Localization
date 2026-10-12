#!/usr/bin/env python3
"""Open urban world (200 x 200 m) + drone (LiDAR+camera+IMU) + ground robot (camera-first), for series B (aerial map -> ground query).
Layout: 4 x 4 blocks of 40 m, 10 m streets between them; each block is split into up to 4 lots with 3 m alleys; heights 4-35 m.
Facades carry a repetitive window texture (a few variants), the ground an asphalt texture.

usage: gen_urban.py [--seed N] [--sun 1.0] [--out urban.sdf]
UNTESTED in Gazebo: topic names / VelocityControl plugin below follow gz-sim defaults; check on the first run.
"""
import argparse
import os
import random
import re
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_world as gw  # noqa: E402

SIZE, BLOCK, ALLEY = 200.0, 40.0, 3.0
CENTERS = [-75, -25, 25, 75]  # block centres on both axes; streets at -50, 0, 50
NFACADE = 4


def make_facade(path, seed, n=1024):
    r = np.random.default_rng(seed)
    wall = np.array([r.uniform(.45, .9), r.uniform(.4, .85), r.uniform(.35, .8)], np.float32)
    img = np.ones((n, n, 3), np.float32) * wall
    img *= cv2.resize(r.random((32, 32, 1), np.float32) * .25 + .85, (n, n))[..., None]  # weathering
    cols, rows = int(r.integers(5, 9)), int(r.integers(6, 11))
    cw, ch = n // cols, n // rows
    for i in range(cols):
        for j in range(rows):
            x0, y0 = i * cw + cw // 5, j * ch + ch // 4
            c = (r.uniform(.1, .35),) * 3 if r.random() > .25 else (r.uniform(.7, .95), r.uniform(.7, .9), r.uniform(.3, .6))
            cv2.rectangle(img, (x0, y0), (x0 + cw * 3 // 5, y0 + ch // 2), [float(v) for v in c], -1)
    cv2.imwrite(path, np.clip(img * 255, 0, 255).astype(np.uint8))


def make_road(path, seed=7, n=4096):
    r = np.random.default_rng(seed)
    img = cv2.resize(r.random((64, 64), np.float32) * .15 + .3, (n, n))[..., None] * np.ones((1, 1, 3), np.float32)
    px = n / SIZE  # lane markings on street centre lines
    for c in (-50, 0, 50):
        p = int((c + SIZE / 2) * px)
        for a in range(0, n, int(6 * px)):
            cv2.line(img, (p, a), (p, a + int(3 * px)), (.9, .9, .85), max(1, int(.2 * px)))
            cv2.line(img, (a, p), (a + int(3 * px), p), (.9, .9, .85), max(1, int(.2 * px)))
    cv2.imwrite(path, np.clip(img * 255, 0, 255).astype(np.uint8))


def lots(rng, cx, cy):
    """split a block into 1-4 lots separated by alleys -> list of (x, y, sx, sy)"""
    h = BLOCK / 2

    def cuts():
        if rng.random() < .25:
            return [(-h, h)]
        m = rng.uniform(-6, 6)
        return [(-h, m - ALLEY / 2), (m + ALLEY / 2, h)]

    return [(cx + (a + b) / 2, cy + (c + d) / 2, b - a - 1, d - c - 1) for a, b in cuts() for c, d in cuts()]


DRONE = """
    <model name="drone">
      <pose>-90 -90 40 0 0 0</pose>
      <link name="base"><gravity>false</gravity>
        <inertial><mass>2</mass><inertia><ixx>0.05</ixx><iyy>0.05</iyy><izz>0.05</izz></inertia></inertial>
        <visual name="v"><geometry><box><size>0.5 0.5 0.15</size></box></geometry><material><diffuse>0.9 0.2 0.2 1</diffuse></material></visual>
        <sensor name="lidar" type="gpu_lidar"><pose>0 0 -0.1 0 0 0</pose>
          <topic>drone/lidar</topic><update_rate>10</update_rate><always_on>true</always_on>
          <lidar><scan>
            <horizontal><samples>1024</samples><min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal>
            <vertical><samples>64</samples><min_angle>-1.4</min_angle><max_angle>0.2</max_angle></vertical></scan>
            <range><min>0.5</min><max>100</max></range>
            <noise><type>gaussian</type><mean>0</mean><stddev>0.02</stddev></noise></lidar></sensor>
        <sensor name="imu" type="imu"><pose>0 0 0 0 0 0</pose><topic>drone/imu</topic><update_rate>200</update_rate><always_on>true</always_on></sensor>
        <sensor name="cam" type="camera"><pose>0.2 0 -0.1 0 0.7 0</pose>
          <topic>drone/camera</topic><update_rate>10</update_rate><always_on>true</always_on>
          <camera><horizontal_fov>1.2</horizontal_fov><image><width>640</width><height>480</height></image>
            <clip><near>0.1</near><far>300</far></clip></camera></sensor>
      </link>
      <plugin filename="gz-sim-velocity-control-system" name="gz::sim::systems::VelocityControl"/>
      <plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
        <publish_link_pose>true</publish_link_pose><publish_sensor_pose>true</publish_sensor_pose><publish_model_pose>true</publish_model_pose>
        <use_pose_vector_msg>true</use_pose_vector_msg><static_publisher>false</static_publisher>
      </plugin>
    </model>"""
# floating body (gravity off) moved by VelocityControl; LiDAR looks down-and-around (vertical -1.4..+0.2 rad), camera pitched 0.7 rad down


def build(seed, sun):
    rng = random.Random(seed)
    parts = []
    for cx in CENTERS:
        for cy in CENTERS:
            for i, (x, y, sx, sy) in enumerate(lots(rng, cx, cy)):
                hgt = rng.choice([4, 6, 8]) if rng.random() < .25 else rng.uniform(10, 35)
                parts.append(gw.box(f"b{cx}_{cy}_{i}", x, y, sx, sy, hgt, (.6, .6, .6), f"fac{rng.randrange(NFACADE)}"))
    robot = gw.ROBOT.replace("<pose>-12 -8 0.15 0 0 0</pose>", "<pose>0 -85 0.15 0 0 1.5708</pose>")
    sdf = gw.build(seed, sun, 0)
    head = sdf[:sdf.index('<model name="ground">')].replace('world name="room"', 'world name="urban"')
    plane = f"<plane><normal>0 0 1</normal><size>{SIZE} {SIZE}</size></plane>"
    ground = (f'<model name="ground"><static>true</static><link name="l"><collision name="c"><geometry>{plane}</geometry></collision>'
              f'<visual name="v"><geometry>{plane}</geometry>{gw.material((.35, .35, .35), "road")}</visual></link></model>')
    return head + ground + "".join(parts) + robot + DRONE + "\n  </world>\n</sdf>\n"


def preview(path):
    """top-down layout PNG from the SDF, to eyeball streets/alleys without Gazebo"""
    s = open(path).read()
    img = np.full((800, 800, 3), 60, np.uint8)
    k = 800 / SIZE
    for m in re.finditer(r'<model name="b[^"]*"><static>true</static><pose>([-\d.]+) ([-\d.]+) ([\d.]+).*?<size>([\d.]+) ([\d.]+) ([\d.]+)', s, re.S):
        x, y, _, sx, sy, sz = map(float, m.groups())
        g = int(80 + sz / 35 * 170)
        cv2.rectangle(img, (int((x - sx / 2 + 100) * k), int((100 - y - sy / 2) * k)),
                      (int((x + sx / 2 + 100) * k), int((100 - y + sy / 2) * k)), (g, g, g), -1)
    cv2.imwrite(path.replace(".sdf", "_layout.png"), img)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--sun", type=float, default=1.0)
    a.add_argument("--out", default="urban.sdf")
    o = a.parse_args()
    d = os.path.dirname(os.path.abspath(o.out))
    for k in range(NFACADE):
        gw.TEX[f"fac{k}"] = f"{d}/tex_fac{k}.png"
        if not os.path.exists(gw.TEX[f"fac{k}"]):
            make_facade(gw.TEX[f"fac{k}"], 10 + k)
    gw.TEX["road"] = f"{d}/tex_road.png"
    if not os.path.exists(gw.TEX["road"]):
        make_road(gw.TEX["road"])
    text = build(o.seed, o.sun)
    open(o.out, "w").write(text)
    preview(o.out)
    print(f"{o.out}: {text.count('<model name=' + chr(34) + 'b')} buildings")
