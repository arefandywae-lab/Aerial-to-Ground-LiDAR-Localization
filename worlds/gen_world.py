#!/usr/bin/env python3
"""Generate a Gazebo world + robot SDF. Variants (light/objects/seed) feed experiments 3,5,7.

usage: gen_world.py [--seed N] [--sun 1.0] [--moved 0.0] [--out world.sdf]
  --sun    sun intensity multiplier (exp 3: lighting change)
  --moved  fraction of boxes removed/shifted vs. the base layout (exp 7: stale map)
"""
import argparse
import os
import random

import cv2
import numpy as np

W, D = 30.0, 20.0  # room size (m)

ROBOT = """
    <model name="robot">
      <pose>-12 -8 0.15 0 0 0</pose>
      <link name="base">
        <inertial><mass>20</mass><inertia><ixx>0.5</ixx><iyy>0.8</iyy><izz>1</izz></inertia></inertial>
        <collision name="c"><geometry><box><size>0.6 0.4 0.2</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>0.6 0.4 0.2</size></box></geometry>
          <material><diffuse>0.2 0.2 0.8 1</diffuse></material></visual>
        <collision name="caster"><pose>-0.25 0 -0.1 0 0 0</pose>
          <geometry><sphere><radius>0.05</radius></sphere></geometry>
          <surface><friction><ode><mu>0</mu><mu2>0</mu2></ode></friction></surface></collision>
        <sensor name="lidar" type="gpu_lidar">
          <pose>0 0 0.35 0 0 0</pose>
          <topic>lidar</topic><update_rate>10</update_rate><always_on>true</always_on>
          <lidar>
            <scan>
              <horizontal><samples>1024</samples><min_angle>-3.14159</min_angle><max_angle>3.14159</max_angle></horizontal>
              <vertical><samples>32</samples><min_angle>-0.5</min_angle><max_angle>0.5</max_angle></vertical>
            </scan>
            <range><min>0.3</min><max>40</max></range>
            <noise><type>gaussian</type><mean>0</mean><stddev>0.01</stddev></noise>
          </lidar>
        </sensor>
        <sensor name="imu" type="imu">
          <pose>0 0 0.2 0 0 0</pose>
          <topic>imu</topic><update_rate>200</update_rate><always_on>true</always_on>
        </sensor>
        <sensor name="cam" type="camera">
          <pose>0.3 0 0.3 0 0 0</pose>
          <topic>camera</topic><update_rate>10</update_rate><always_on>true</always_on>
          <camera>
            <horizontal_fov>1.2</horizontal_fov>
            <image><width>640</width><height>480</height></image>
            <clip><near>0.1</near><far>100</far></clip>
          </camera>
        </sensor>
      </link>
      <link name="lwheel"><pose relative_to="base">0 0.25 0 -1.5708 0 0</pose>
        <inertial><mass>1</mass><inertia><ixx>0.01</ixx><iyy>0.01</iyy><izz>0.01</izz></inertia></inertial>
        <collision name="c"><geometry><cylinder><radius>0.15</radius><length>0.05</length></cylinder></geometry></collision>
        <visual name="v"><geometry><cylinder><radius>0.15</radius><length>0.05</length></cylinder></geometry></visual></link>
      <link name="rwheel"><pose relative_to="base">0 -0.25 0 -1.5708 0 0</pose>
        <inertial><mass>1</mass><inertia><ixx>0.01</ixx><iyy>0.01</iyy><izz>0.01</izz></inertia></inertial>
        <collision name="c"><geometry><cylinder><radius>0.15</radius><length>0.05</length></cylinder></geometry></collision>
        <visual name="v"><geometry><cylinder><radius>0.15</radius><length>0.05</length></cylinder></geometry></visual></link>
      <joint name="lj" type="revolute"><parent>base</parent><child>lwheel</child>
        <axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>
      <joint name="rj" type="revolute"><parent>base</parent><child>rwheel</child>
        <axis><xyz>0 0 1</xyz><limit><lower>-1e16</lower><upper>1e16</upper></limit></axis></joint>
      <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
        <left_joint>lj</left_joint><right_joint>rj</right_joint>
        <wheel_separation>0.5</wheel_separation><wheel_radius>0.15</wheel_radius>
        <topic>cmd_vel</topic>
      </plugin>
      <!-- ground truth pose of every link, world frame -->
      <plugin filename="gz-sim-pose-publisher-system" name="gz::sim::systems::PosePublisher">
        <publish_link_pose>true</publish_link_pose><publish_sensor_pose>true</publish_sensor_pose>
        <publish_model_pose>true</publish_model_pose>
        <use_pose_vector_msg>true</use_pose_vector_msg><static_publisher>false</static_publisher>
      </plugin>
    </model>
"""


TEX = {}  # kind -> png path; empty = plain colours (exp 5: low-texture world)


def make_tex(path, seed, tint, n=4096):
    """Blob + hard-edged shape texture; n px square (walls/floor are stretched over 20-30 m, so go big)."""
    r = np.random.default_rng(seed)
    k = n / 1024
    base = cv2.resize(r.random((48, 48, 3), np.float32), (n, n), interpolation=cv2.INTER_CUBIC)
    fine = cv2.resize(r.random((n // 8, n // 8, 3), np.float32), (n, n), interpolation=cv2.INTER_CUBIC)
    img = (0.75 * base + 0.25 * fine) * np.array(tint, np.float32)
    for _ in range(int(900 * k * k)):  # hard-edged shapes give SIFT corners
        c = [float(v) for v in r.random(3)]
        p = tuple(int(v) for v in r.integers(0, n, 2))
        w = int(r.integers(int(12 * k), int(110 * k)))
        if r.random() < .5:
            cv2.circle(img, p, w // 2, c, -1)
        else:
            cv2.rectangle(img, p, (p[0] + w, p[1] + int(w * r.uniform(.4, 1.6))), c, -1)
    cv2.imwrite(path, np.clip(img * 255, 0, 255).astype(np.uint8))


def material(rgb, kind):
    if kind in TEX:
        return (f"<material><diffuse>1 1 1 1</diffuse><pbr><metal><albedo_map>{TEX[kind]}</albedo_map>"
                f"<roughness>1</roughness><metalness>0</metalness></metal></pbr></material>")
    return f"<material><diffuse>{rgb[0]:.2f} {rgb[1]:.2f} {rgb[2]:.2f} 1</diffuse></material>"


def box(name, x, y, sx, sy, sz, rgb, kind="box"):
    return f"""
    <model name="{name}"><static>true</static><pose>{x:.2f} {y:.2f} {sz/2:.2f} 0 0 0</pose>
      <link name="l">
        <collision name="c"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry></collision>
        <visual name="v"><geometry><box><size>{sx} {sy} {sz}</size></box></geometry>
          {material(rgb, kind)}</visual>
      </link></model>"""


DISTINCT = False  # --distinct: one texture per wall and per box


def build(seed, sun, moved):
    rng = random.Random(seed)
    parts = []
    # perimeter walls
    for n, x, y, sx, sy in [("wn", 0, D/2, W, .3), ("ws", 0, -D/2, W, .3),
                            ("we", W/2, 0, .3, D), ("ww", -W/2, 0, .3, D)]:
        parts.append(box(n, x, y, sx, sy, 3, (.75, .72, .65), f"wall_{n}" if DISTINCT else "wall"))
    # obstacles; layout fixed by seed, `moved` drops/shifts a fraction (rng stream kept identical)
    mrng = random.Random(seed + 1000)
    for i in range(18):
        x, y = rng.uniform(-9, 9), rng.uniform(-5, 5)
        s = [rng.uniform(.5, 2) for _ in range(3)]
        c = (rng.random(), rng.random(), rng.random())
        if mrng.random() < moved:
            if mrng.random() < .5:
                continue
            x, y = x + 1.0, y + 1.0
        parts.append(box(f"obj{i}", x, y, s[0], s[1], s[2] + .5, c, f"box_{i}" if DISTINCT else "box"))
    return f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="room">
    <physics type="ignored"><max_step_size>0.004</max_step_size><real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <scene><ambient>{.4*sun:.2f} {.4*sun:.2f} {.4*sun:.2f} 1</ambient></scene>
    <light type="directional" name="sun"><cast_shadows>true</cast_shadows>
      <diffuse>{.8*sun:.2f} {.8*sun:.2f} {.8*sun:.2f} 1</diffuse><direction>-0.5 0.3 -0.9</direction></light>
    <model name="ground"><static>true</static><link name="l">
      <collision name="c"><geometry><plane><normal>0 0 1</normal><size>{W} {D}</size></plane></geometry></collision>
      <visual name="v"><geometry><plane><normal>0 0 1</normal><size>{W} {D}</size></plane></geometry>
        {material((.5, .5, .5), "floor")}</visual></link></model>
    {"".join(parts)}
    {ROBOT}
  </world>
</sdf>
"""


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--sun", type=float, default=1.0)
    a.add_argument("--moved", type=float, default=0.0)
    a.add_argument("--tex", type=int, default=1, help="0 = plain colours (low-texture world)")
    a.add_argument("--distinct", type=int, default=0, help="1 = unique texture per wall and per box (no repeated appearance)")
    a.add_argument("--out", default="room.sdf")
    o = a.parse_args()
    DISTINCT = bool(o.distinct)
    if o.tex:
        d = os.path.dirname(os.path.abspath(o.out))
        for k, tint in [("wall", (1, .95, .85)), ("floor", (.9, .9, .9)), ("box", (1, 1, 1))]:
            TEX[k] = f"{d}/tex_{k}.png"
            if not os.path.exists(TEX[k]):  # fixed seed per kind: map and query worlds share textures
                make_tex(TEX[k], {"wall": 1, "floor": 2, "box": 3}[k], tint, 1024 if k == "box" else 4096)
    if o.tex and DISTINCT:
        for n in ("wn", "ws", "we", "ww"):
            TEX[f"wall_{n}"] = f"{d}/tex_wall_{n}.png"
            if not os.path.exists(TEX[f"wall_{n}"]):
                make_tex(TEX[f"wall_{n}"], 100 + ["wn", "ws", "we", "ww"].index(n), (1, .95, .85), 4096)
        for i in range(18):
            TEX[f"box_{i}"] = f"{d}/tex_box_{i}.png"
            if not os.path.exists(TEX[f"box_{i}"]):
                make_tex(TEX[f"box_{i}"], 200 + i, (1, 1, 1), 1024)
    open(o.out, "w").write(build(o.seed, o.sun, o.moved))
