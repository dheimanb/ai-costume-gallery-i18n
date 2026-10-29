# -*- coding: utf-8 -*-
from pathlib import Path
import json, re
html = Path(r"E:\costume-staging\raw\index.html").read_text(encoding="utf-8")
# find raw key bytes around first item
idx = html.find('const D=[')
snippet = html[idx:idx+400]
Path(r"E:\costume-staging\meta\snippet_hex.txt").write_text(
    "\n".join(f"{i:04d} U+{ord(c):04X} {c!r}" for i,c in enumerate(snippet[:200])),
    encoding="utf-8"
)
data = json.loads(Path(r"E:\costume-staging\raw\D.json").read_text(encoding="utf-8"))
meta = json.loads(Path(r"E:\costume-staging\meta\META.json").read_text(encoding="utf-8"))
keys = list(data[0].keys())
report = []
report.append("KEYS:")
for k in keys:
    report.append(f"  {k!r} -> " + " ".join(f"U+{ord(c):04X}" for c in k))
report.append("CATS:")
for c in meta["cats"]:
    report.append(f"  {c!r} -> " + " ".join(f"U+{ord(c):04X}" for c in c))
report.append(f"counts={meta['counts']}")
report.append(f"len={len(data)}")
# verify all items have same keys and non-empty paths
bad = []
for i, item in enumerate(data):
    if list(item.keys()) != keys:
        bad.append(("keys", item.get("id")))
    for k in keys[3:]:  # path fields - wait identify by value pattern
        pass
# identify path fields by value
path_keys = [k for k in keys if isinstance(data[0][k], str) and ("/" in str(data[0][k]) or str(data[0][k]).endswith(('.webp','.png','.jpg')))]
cat_key = [k for k in keys if k != "id" and data[0][k] in meta["cats"]][0]
kw_key = [k for k in keys if k not in ("id", cat_key) and k not in path_keys][0]
report.append(f"cat_key={cat_key!r}")
report.append(f"kw_key={kw_key!r}")
report.append(f"path_keys={[repr(k) for k in path_keys]}")
# path prefix check
from collections import Counter
for pk in path_keys:
    prefs = Counter(str(x[pk]).split("/")[0] for x in data)
    report.append(f"path {pk!r} prefixes={dict(prefs)}")
# empty / missing
for pk in path_keys:
    empties = [x["id"] for x in data if not x.get(pk)]
    report.append(f"empty {pk!r}: {len(empties)}")
Path(r"E:\costume-staging\meta\codepoints.txt").write_text("\n".join(report), encoding="utf-8")
print("wrote codepoints")