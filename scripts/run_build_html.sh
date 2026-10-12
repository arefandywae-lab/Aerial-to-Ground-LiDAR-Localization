pip install --quiet --break-system-packages markdown 2>&1 | grep -v WARNING | tail -n 1
cd /mnt/a/SlamProject && python3 scripts/build_report_html.py
