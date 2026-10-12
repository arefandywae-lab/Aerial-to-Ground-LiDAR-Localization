pip install --quiet --break-system-packages pypdf 2>&1 | grep -v WARNING | tail -n 1
cd /mnt/a/SlamProject && python3 scripts/pdf2txt.py
