"""One-off patch (repo root): urban_diag.py takes the query session from DIAG_QUERIES (default ug1s) and saves per-query diagnosis arrays, so failures can be analysed per street segment."""
import io

p = "scripts/urban_diag.py"
s = io.open(p, encoding="utf-8").read()
assert 'load_session("/root/data/ug1s_img")' in s
s = s.replace('import sys\nfrom concurrent', 'import os\nimport sys\nfrom concurrent', 1)
s = s.replace('q = load_session("/root/data/ug1s_img")', 'QS = os.environ.get("DIAG_QUERIES", "/root/data/ug1s_img")\nq = load_session(QS)', 1)
s = s.replace('print(f"D3 median coloured fraction of oracle views {np.median(col):.2f}")',
              'print(f"D3 median coloured fraction of oracle views {np.median(col):.2f}")\n'
              'hit50 = np.take_along_axis(close, rank[:, :50], 1).any(1)  # a close view is among the MegaLoc top-50\n'
              'out = os.environ.get("DIAG_OUT")\n'
              'if out:\n'
              '    np.savez(out, hit50=hit50, has_close=has, oracle_ok=ok55, oracle_matches=rows[:, 0], oracle_inl=rows[:, 1], oracle_dpos=dpos[np.arange(len(pq)), oracle], colour=col, pos=pq)\n'
              '    print("saved", out)', 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")
