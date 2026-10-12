#!/bin/bash
# Dataset v2 end to end: record (collect_v2.sh) -> FAST-LIO2 on s0v2 -> ATE -> world-frame coloured map -> M0 and M1-LoFTR(f0c1) x 3 seeds on q1v2, q2v2.
set -e
cd /root  # never leave cwd on the NTFS mount
R=/mnt/a/SlamProject
source /opt/ros/jazzy/setup.bash
rm -rf /root/data/vp /root/data/vp_img /root/data/vp_sorted
bash $R/scripts/collect_v2.sh   # skips sessions already recorded
source /root/ws/install/setup.bash
echo "=== FAST-LIO2 on s0v2 ==="
bash $R/ros/run_lio.sh /root/data/s0v2 /root/data/lio_s0v2 > /root/data/lio_s0v2.log 2>&1
cat /root/data/lio_s0v2/resort.log
cd $R/ros
python3 eval_ate.py /root/data/s0v2 /root/data/lio_s0v2/odom | tee $R/results/ate_s0v2.txt
python3 build_map.py /root/data/lio_s0v2/odom /root/data/lio_s0v2/map.npy
python3 $R/vps/build_lidar_map.py /root/data/s0v2 /root/data/lio_s0v2/odom /root/data/lio_s0v2/map.npy /root/data/s0v2_img /root/data/map_s0v2.npz
cd $R/vps
export M1_MAP=/root/data/map_s0v2.npz
for q in q1v2 q2v2; do
  for s in 0 1 2; do
    python3 harness.py --method m0 --map /root/data/s0v2_img --queries /root/data/${q}_img --out ../results/v2/m0_${q}_s$s.json --seed $s > /dev/null 2>&1
    M1LF_FP16=0 M1LF_COARSE=1 python3 harness.py --method m1lf --map /root/data/s0v2_img --queries /root/data/${q}_img \
      --out ../results/v2/m1lf_${q}_s$s.json --seed $s > /dev/null 2>&1
    echo "done $q seed $s"
  done
done
echo PIPELINE_DONE
