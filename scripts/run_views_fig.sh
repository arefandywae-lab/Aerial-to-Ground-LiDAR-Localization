cd /mnt/a/SlamProject/vps
export M1_ZFAR=120 M1_SPLAT=0.12 M1_RMAX=4 M1_MAP=/root/data/map_ud0_f2.npz
python3 /mnt/a/SlamProject/scripts/make_views_figure.py /mnt/a/SlamProject/docs/figures/drone_vs_robot_views.png 2>&1 | grep -v -i warn | tail -n 4
