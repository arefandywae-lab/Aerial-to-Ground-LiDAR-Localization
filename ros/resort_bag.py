#!/usr/bin/env python3
"""Rewrite a session bag so receive (log) time follows sim time. `ros2 bag play` replays in log-time order, and under recorder load
some messages arrive ~0.5 s late, which FAST-LIO sees as IMU/LiDAR time going backwards ("imu loop back" -> buffer cleared).
Key per message: header.stamp (sensors), clock value (/clock), first transform stamp (/gt/model); unstamped topics (/gt/poses)
get the newest /clock value received before them (only the driver uses that topic).
usage: resort_bag.py IN_BAG OUT_BAG [topic ...]   (default: the FAST-LIO replay set; the whole bag is held in RAM, so keep images out)"""
import sys

from rclpy.serialization import deserialize_message
from rosbag2_py import ConverterOptions, SequentialReader, SequentialWriter, StorageOptions, TopicMetadata
from rosidl_runtime_py.utilities import get_message


def key(topic, m, last_clock):
    if topic == "/clock":
        return m.clock.sec + m.clock.nanosec * 1e-9
    if hasattr(m, "header"):
        return m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    if topic == "/gt/model" and m.transforms:
        s = m.transforms[0].header.stamp
        return s.sec + s.nanosec * 1e-9
    return last_clock


DEFAULT_TOPICS = ["/clock", "/imu", "/lidar/points"]


def main(src, dst, keep=DEFAULT_TOPICS):
    r = SequentialReader()
    r.open(StorageOptions(uri=src, storage_id="mcap"), ConverterOptions("", ""))
    topics = [t for t in r.get_all_topics_and_types() if t.name in keep]
    types = {t.name: get_message(t.type) for t in topics}
    rows, last_clock, t0_log = [], 0.0, None
    while r.has_next():
        topic, data, ts = r.read_next()
        if topic not in types:
            continue
        t0_log = ts if t0_log is None else t0_log
        k = key(topic, deserialize_message(data, types[topic]), last_clock)
        if topic == "/clock":
            last_clock = max(last_clock, k)
        rows.append((k, len(rows), topic, data))
    rows.sort()  # stable on ties via the original index
    sim0 = next(k for k, _, t, _ in rows if t == "/clock")
    w = SequentialWriter()
    w.open(StorageOptions(uri=dst, storage_id="mcap"), ConverterOptions("", ""))
    for i, t in enumerate(topics):
        w.create_topic(TopicMetadata(id=i, name=t.name, type=t.type, serialization_format="cdr"))
    moved = 0
    prev = None
    for k, idx, topic, data in rows:
        w.write(topic, data, t0_log + int(max(0.0, k - sim0) * 1e9))
        moved += prev is not None and idx < prev
        prev = idx
    del w
    print(f"{dst}: {len(rows)} msgs, {moved} moved back relative to receive order")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or DEFAULT_TOPICS)
