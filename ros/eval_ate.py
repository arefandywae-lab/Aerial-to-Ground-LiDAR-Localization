#!/usr/bin/env python3
"""ATE / RPE of FAST-LIO2 /Odometry vs Gazebo GT.
usage: eval_ate.py SESSION_BAG ODOM_BAG
GT = first transform of /gt/poses (robot in world). The TFMessage has no stamp, so GT bag log-time is
mapped to sim time through /clock samples. Estimate is rigidly aligned to GT (Umeyama, no scale)."""
import sys

import numpy as np
from scipy.spatial.transform import Rotation as Rot
from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, StorageOptions
from rosidl_runtime_py.utilities import get_message


def read(path, topics):
    r = SequentialReader()
    r.open(StorageOptions(uri=path, storage_id="mcap"), ConverterOptions("", ""))
    types = {t.name: get_message(t.type) for t in r.get_all_topics_and_types()}
    out = {t: [] for t in topics}
    while r.has_next():
        t, d, ts = r.read_next()
        if t in out:
            out[t].append((ts * 1e-9, deserialize_message(d, types[t])))
    return out


def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0)
    U, _, Vt = np.linalg.svd((dst - md).T @ (src - ms) / len(src))
    S = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    R = U @ S @ Vt
    return R, md - R @ ms


IMU_IN_BASE = np.array([0.0, 0.0, 0.2])  # gen_world.py: imu sensor pose in base link; FAST-LIO body frame = IMU


def gt_track(bag, model="robot", topic="/gt/model"):
    """Robot (model origin = base link) pose in world from a session bag -> (t_sim (N,), pos (N,3), quat xyzw (N,4)), t strictly increasing.
    Preferred: /gt/model (PosePublisher, per-pose sim-time stamp + frame names). Legacy bags (v1) only have /gt/poses, whose
    bridged messages carry NO stamp, so their time must come from bag receive time mapped through /clock receive times; that is
    only valid if messages were received in order, which is checked (a recorder under load delivers some messages ~0.5 s late)."""
    d = read(bag, ["/clock", "/gt/poses", topic])
    if d[topic]:
        rows = [(x.header.stamp.sec + x.header.stamp.nanosec * 1e-9, x.transform)
                for _, m in d[topic] for x in m.transforms if x.child_frame_id == model]
        assert rows, f"{topic} has no transform with child_frame_id == {model!r}"
        rows.sort(key=lambda r: r[0])
        t = np.array([r[0] for r in rows])
        keep = np.r_[True, np.diff(t) > 0]  # duplicates of one stamp (re-delivery) carry the same pose
        tr = [r[1] for r, k in zip(rows, keep) if k]
        t = t[keep]
    else:
        clk = np.array([(t, m.clock.sec + m.clock.nanosec * 1e-9) for t, m in d["/clock"]])
        if np.any(np.diff(clk[:, 1]) <= 0):
            raise ValueError(f"{bag}: /clock not monotonic in receive order ({int((np.diff(clk[:, 1]) <= 0).sum())} steps) and GT is "
                             "unstamped; GT timing would be wrong. Re-record with /gt/model.")
        t = np.interp([lt for lt, _ in d["/gt/poses"]], clk[:, 0], clk[:, 1])
        # positional: legacy bridged TFMessage has empty frame ids; room world publishes [model, base, lwheel, rwheel], [0] = model pose
        assert all(len(m.transforms) == 4 for _, m in d["/gt/poses"]), "unexpected /gt/poses layout; positional GT selection invalid"
        tr = [m.transforms[0].transform for _, m in d["/gt/poses"]]
        assert np.all(np.diff(t) > 0), "legacy GT times not strictly increasing"
    pos = np.array([[x.translation.x, x.translation.y, x.translation.z] for x in tr])
    q = np.array([[x.rotation.x, x.rotation.y, x.rotation.z, x.rotation.w] for x in tr])
    return t, pos, q


def sensor_in_base(bag, frame, topic="/gt/model"):
    """Static pose of a sensor frame (e.g. 'robot/base/cam') relative to its parent link, read from the first stamped GT message of the bag,
    so camera/IMU extrinsics need not be hard-coded per vehicle. -> (translation (3,), quaternion xyzw (4,))."""
    d = read(bag, [topic])[topic]
    for _, m in d:
        for x in m.transforms:
            if x.child_frame_id == frame:
                t, r = x.transform.translation, x.transform.rotation
                return np.array([t.x, t.y, t.z]), np.array([r.x, r.y, r.z, r.w])
    raise KeyError(f"{frame!r} not found in {topic}")


def align(sess_bag, odom_bag, model="robot", topic="/gt/model"):
    """Rigidly align FAST-LIO camera_init frame to the Gazebo world using GT IMU positions.
    Returns dict(R, t, err (per pose), path_m, gt, est): world = R @ camera_init + t."""
    gt_t, pos, q = gt_track(sess_bag, model, topic)
    try:  # stamped bags carry the IMU extrinsic; legacy (v1) bags use the ground-robot constant
        imu_off, _ = sensor_in_base(sess_bag, f"{model}/base/imu", topic)
    except (KeyError, Exception):
        imu_off = IMU_IN_BASE
    gt = pos + Rot.from_quat(q).apply(imu_off)
    od = read(odom_bag, ["/Odometry"])["/Odometry"]
    et = np.array([m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 for _, m in od])
    ep = np.array([[m.pose.pose.position.x, m.pose.pose.position.y, m.pose.pose.position.z] for _, m in od])
    keep = (et >= gt_t[0]) & (et <= gt_t[-1])
    et, ep = et[keep], ep[keep]
    g = np.stack([np.interp(et, gt_t, gt[:, i]) for i in range(3)], 1)
    R, t = umeyama(ep, g)
    err = np.linalg.norm((ep @ R.T + t) - g, axis=1)
    keep = np.ones(len(ep), bool)
    for _ in range(6):  # trimmed re-fit: a few outlier poses (the first seconds of a flight) must not pull the alignment of the whole map
        keep = err < max(3.0 * np.median(err[keep]), 0.5)
        if keep.sum() < 20:
            break
        R, t = umeyama(ep[keep], g[keep])
        err = np.linalg.norm((ep @ R.T + t) - g, axis=1)
    return dict(R=R, t=t, err=err, gt=g, est=ep, keep=keep)


if __name__ == "__main__":
    a_ = align(sys.argv[1], sys.argv[2], *(sys.argv[3:5]))  # optional: model frame, GT topic
    err, g, ep, R = a_["err"], a_["gt"], a_["est"], a_["R"]
    kp = a_.get("keep", np.ones(len(err), bool))
    path = np.linalg.norm(np.diff(g, axis=0), axis=1).sum()
    step = max(1, int(len(g) * 0.1))  # RPE over ~10% of the trajectory
    rpe = np.linalg.norm(((ep[step:] - ep[:-step]) @ R.T) - (g[step:] - g[:-step]), axis=1)
    print(f"poses={len(ep)} path={path:.1f}m  ATE rmse={np.sqrt((err**2).mean()):.3f}m "
          f"max={err.max():.3f}m (trimmed fit: {kp.sum()}/{len(err)} poses used, rmse on those {np.sqrt((err[kp]**2).mean()):.3f}m, max {err[kp].max():.3f}m)  RPE(10%) mean={rpe.mean():.3f}m  drift={100*err[-1]/path:.2f}% of path")
