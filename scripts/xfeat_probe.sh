cd /mnt/a/SlamProject
python3 - <<'PY' 2>&1 | grep -v -i warn
import kornia.feature as f, inspect
print(inspect.signature(f.XFeat.__init__)); print(inspect.signature(f.XFeat.forward))
print([m for m in dir(f.XFeat) if not m.startswith('_')])
print(inspect.signature(f.LightGlue.__init__))
PY
