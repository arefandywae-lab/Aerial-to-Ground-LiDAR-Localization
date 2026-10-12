"""One-off patch: read camera extrinsics from the bag instead of hard-coding them (TODO A14). Idempotent guard via asserts."""
import io

p = "ros/eval_ate.py"
s = io.open(p, encoding="utf-8").read()
assert "def sensor_in_base" not in s
s = s.replace('def gt_track(bag, model="robot"):', 'def gt_track(bag, model="robot", topic="/gt/model"):')
s = s.replace('    d = read(bag, ["/clock", "/gt/poses", "/gt/model"])\n    if d["/gt/model"]:',
              '    d = read(bag, ["/clock", "/gt/poses", topic])\n    if d[topic]:')
s = s.replace('for _, m in d["/gt/model"] for x in m.transforms if x.child_frame_id == model]',
              'for _, m in d[topic] for x in m.transforms if x.child_frame_id == model]')
s = s.replace('assert rows, f"/gt/model has no transform with child_frame_id == {model!r}"',
              'assert rows, f"{topic} has no transform with child_frame_id == {model!r}"')
new_fn = '''def sensor_in_base(bag, frame, topic="/gt/model"):
    """Static pose of a sensor frame (e.g. 'robot/base/cam') relative to its parent link, read from the first stamped GT message of the bag,
    so camera/IMU extrinsics need not be hard-coded per vehicle. -> (translation (3,), quaternion xyzw (4,))."""
    d = read(bag, [topic])[topic]
    for _, m in d:
        for x in m.transforms:
            if x.child_frame_id == frame:
                t, r = x.transform.translation, x.transform.rotation
                return np.array([t.x, t.y, t.z]), np.array([r.x, r.y, r.z, r.w])
    raise KeyError(f"{frame!r} not found in {topic}")


def align(sess_bag, odom_bag):'''
assert "def align(sess_bag, odom_bag):" in s
s = s.replace("def align(sess_bag, odom_bag):", new_fn, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)

p = "vps/dump_session.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace("from eval_ate import gt_track, read  # noqa: E402", "from eval_ate import gt_track, read, sensor_in_base  # noqa: E402")
old = '''def main(bag, out, every=1):
    gt_t, pos, quat = gt_track(bag)
    slerp = Slerp(gt_t, Rot.from_quat(quat))
    d = read(bag, ["/camera/image_raw", "/camera/camera_info"])
    ci = d["/camera/camera_info"][0][1]'''
new = '''def main(bag, out, every=1, frame="robot", gt_topic="/gt/model", image="/camera/image_raw", info="/camera/camera_info", cam_frame=None):
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
    ci = d[info][0][1]'''
assert old in s
s = s.replace(old, new)
s = s.replace('imgs = sorted((m for _, m in d["/camera/image_raw"]), key=stamp)', "imgs = sorted((m for _, m in d[image]), key=stamp)")
old = '''        Tw[:3, :3] = Rb @ CV2GZ
        Tw[:3, 3] = pb + Rb @ np.array(CAM_IN_BASE)'''
assert old in s
s = s.replace(old, '''        Tw[:3, :3] = Rb @ R_bc @ CV2GZ  # world <- base <- gazebo camera frame <- OpenCV optical frame
        Tw[:3, 3] = pb + Rb @ t_bc''')
old = '''if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)'''
assert old in s
s = s.replace(old, '''if __name__ == "__main__":
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
    main(o.bag, o.out, o.every, o.frame, o.gt_topic, o.image, o.info, o.cam_frame)''')
s = s.replace("usage: dump_session.py SESSION_BAG OUT_DIR [every_n=1]",
              "usage: dump_session.py SESSION_BAG OUT_DIR [every_n=1] [--frame drone --gt-topic /gt/drone --image /drone/camera/image_raw --info /drone/camera/camera_info]")
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
