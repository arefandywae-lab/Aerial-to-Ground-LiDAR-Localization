"""PDF -> text for searching (docs/papers_txt/*.txt, one per paper, with ===== PAGE n ===== markers). usage: pdf2txt.py"""
import os, glob
from pypdf import PdfReader
os.makedirs("/mnt/a/SlamProject/docs/papers_txt", exist_ok=True)
for f in sorted(glob.glob("/mnt/a/SlamProject/docs/papers/*.pdf")):
    out = "/mnt/a/SlamProject/docs/papers_txt/" + os.path.basename(f)[:-4] + ".txt"
    r = PdfReader(f); txt = []
    for i, p in enumerate(r.pages):
        try: t = p.extract_text() or ""
        except Exception as e: t = f"[extract error {e}]"
        txt.append(f"\n===== PAGE {i+1} =====\n" + t)
    open(out, "w", encoding="utf-8", errors="replace").write("".join(txt)); print(os.path.basename(f), len(r.pages), "pages,", sum(map(len, txt)), "chars")
