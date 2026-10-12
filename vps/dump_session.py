#!/usr/bin/env python3
"""Session bag -> images + GT camera poses.
usage: dump_session.py SESSION_BAG OUT_DIR [every_n=1] [--frame drone --gt-topic /gt/drone --image /drone/camera/image_raw --info /drone/camera/camera_info]
OUT/images/%05d.png (BGR), OUT/poses.npy (N,4,4 camera-to-world, OpenCV optical: x right, y down, z fwd),
OUT/K.npy (3x3), OUT/stamps.npy. Image and GT times are sim-time stamps (eval_ate.gt_track); images are written in stamp order."""
import os
import sys

import cv2
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ros"))
from eval_ate import gt_track, read, sensor_in_base  # noqa: E402

CAM_IN_BASE = (0.3, 0.0, 0.3)  # gen_world.py: camera sensor pose in base link
CV2GZ = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], float)  # columns: optical x,y,z axes expressed in gazebo cam frame (x fwd,y left,z up)


def main(bag, out, every=1, frame="robot", gt_topic="/gt/model", image="/camera/image_raw", info="/camera/camera_info", cam_frame=None):
    """frame: vehicle model frame in the GT topic. cam_frame: sensor frame whose extrinsic is read from the bag (default <frame>/base/cam
    when the bag has stamped GT, else the legacy hard-coded ground-robot offset)."""
    gt_t, pos, quat = gt_track(bag, frame, gt_topic)
    slerp = Slerp(gt_t, Rot.from_quat(quat))
    d = read(bag, [image, info])
    try:
        cam_frame = cam_frame or f"{frame}/base/cam"
        t_bc, q_bc = sensor_in_base(bag, cam_frame, gt_topic)
        R_bc = Rot.from_quat(q_bc).as_matrix()
        print(f"camera extrinsic from bag ({cam_frame}): t={t_bc.round(3)}, gazebo camera x-axis in base = {R_bc[:, 0].round(3)}")
    except KeyError:
        t_bc, R_bc = np.array(CAM_IN_BASE), np.eye(3)  # legacy bags without sensor frames
        print("camera extrinsic: legacy hard-coded ground-robot offset")
    ci = d[info][0][1]
    K = np.array(ci.k).reshape(3, 3)
    os.makedirs(f"{out}/images", exist_ok=True)
    T, S = [], []
    stamp = lambda m: m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    imgs = sorted((m for _, m in d[image]), key=stamp)  # receive order can be shuffled; M0 assumes index = time order
    for i, m in enumerate(imgs):
        t = stamp(m)
        if i % every or not gt_t[0] <= t <= gt_t[-1]:
            continue
        Rb = slerp([t]).as_matrix()[0]
        pb = np.array([np.interp(t, gt_t, pos[:, k]) for k in range(3)])
        Tw = np.eye(4)
        Tw[:3, :3] = Rb @ R_bc @ CV2GZ  # world <- base <- gazebo camera frame <- OpenCV optical frame
        Tw[:3, 3] = pb + Rb @ t_bc
        assert m.encoding in ("rgb8", "bgr8") and m.step == m.width * 3, f"unexpected image: enc={m.encoding} step={m.step}"
        img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.width, 3)
        cv2.imwrite(f"{out}/images/{len(T):05d}.png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if m.encoding == "rgb8" else img)
        T.append(Tw)
        S.append(t)
    np.save(f"{out}/poses.npy", np.array(T))
    np.save(f"{out}/K.npy", K)
    np.save(f"{out}/stamps.npy", np.array(S))
    print(f"{out}: {len(T)} images, K fx={K[0,0]:.1f} cx={K[0,2]:.1f}")


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("bag")
    a.add_argument("out")
    a.add_argument("every", nargs="?", type=int, default=1)
    a.add_argument("--frame", default="robot", help="vehicle frame in the GT topic (drone: 'drone')")
    a.add_argument("--gt-topic", default="/gt/model")
    a.add_argument("--image", default="/camera/image_raw")
    a.add_argument("--info", default="/camera/camera_info")
    a.add_argument("--cam-frame", default=None)
    o = a.parse_args()
    main(o.bag, o.out, o.every, o.frame, o.gt_topic, o.image, o.info, o.cam_frame)
