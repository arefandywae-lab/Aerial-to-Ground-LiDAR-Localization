"""docs/REPORT.md -> docs/REPORT.html: one self-contained file (figures embedded as base64, print-friendly CSS) that can be sent as is and printed to PDF from a browser.
usage: python scripts/build_report_html.py   (run from the repo root; needs the `markdown` package)"""
import base64
import mimetypes
import re
from pathlib import Path

import markdown

root = Path(__file__).resolve().parent.parent
src = (root / "docs" / "REPORT.md").read_text(encoding="utf-8")
html = markdown.markdown(src, extensions=["tables", "fenced_code", "sane_lists"])


def embed(m):
    p = root / "docs" / m.group(1)
    if not p.exists():
        return m.group(0)
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f'src="data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"'


html = re.sub(r'src="([^"]+\.(?:png|jpg|jpeg))"', embed, html)
css = """
body{font-family:'Segoe UI','Noto Sans Thai','Sarabun',Tahoma,sans-serif;max-width:980px;margin:32px auto;padding:0 20px;line-height:1.65;color:#1b1f23}
h1{font-size:1.7em;border-bottom:2px solid #d0d7de;padding-bottom:.3em} h2{font-size:1.35em;margin-top:1.8em;border-bottom:1px solid #d0d7de;padding-bottom:.2em} h3{font-size:1.1em;margin-top:1.4em}
table{border-collapse:collapse;margin:1em 0;font-size:.92em;width:100%} th,td{border:1px solid #d0d7de;padding:6px 9px;vertical-align:top} th{background:#f3f4f6;text-align:left}
code{background:#f3f4f6;padding:1px 5px;border-radius:4px;font-size:.9em} img{max-width:100%;height:auto;border:1px solid #d0d7de;border-radius:6px}
blockquote{border-left:4px solid #d0d7de;margin:1em 0;padding:.2em 1em;color:#57606a} a{color:#0969da}
@media print{body{max-width:none;margin:0} h2{page-break-after:avoid} table,img{page-break-inside:avoid}}
"""
out = root / "docs" / "REPORT.html"
out.write_text(f'<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
               f"<title>รายงานการทดลอง: หาตำแหน่งหุ่นกล้องเดียวใน map ที่โดรนสร้าง</title><style>{css}</style></head><body>{html}</body></html>", encoding="utf-8")
print(out, round(out.stat().st_size / 1024), "KB,", html.count("<table"), "tables,", html.count("<img"), "images")
