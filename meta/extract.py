# -*- coding: utf-8 -*-
from pathlib import Path
import re, json
html = Path(r"E:\costume-staging\raw\index.html").read_text(encoding="utf-8")
m = re.search(r"const META=(\{.*?\});", html, re.S)
d = re.search(r"const D=(\[.*?\]);\s*\nconst PAGE", html, re.S)
assert m and d, "parse fail"
meta = json.loads(m.group(1))
data = json.loads(d.group(1))
Path(r"E:\costume-staging\meta\META.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
Path(r"E:\costume-staging\raw\D.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
# report keys and sample
keys = list(data[0].keys())
out = {
  "total_meta": meta.get("total"),
  "len_D": len(data),
  "cats": meta.get("cats"),
  "counts": meta.get("counts"),
  "keys": keys,
  "sample0": data[0],
  "sample_last": data[-1],
  "id_prefix_counts": {}
}
from collections import Counter
c = Counter(x["id"].split("-")[0] for x in data)
out["id_prefix_counts"] = dict(c)
Path(r"E:\costume-staging\meta\extract_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("OK", len(data), keys)