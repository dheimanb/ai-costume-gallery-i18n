# -*- coding: utf-8 -*-
"""Extract vocab CSV + prepare download manifest from immutable D.json."""
from pathlib import Path
import json, csv

ROOT = Path(r"E:\costume-staging")
data = json.loads((ROOT / "raw" / "D.json").read_text(encoding="utf-8"))
meta = json.loads((ROOT / "meta" / "META.json").read_text(encoding="utf-8"))

# vocab CSV: id, JP category, keywords (English keyword string as on site)
csv_path = ROOT / "meta" / "vocab.csv"
with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "カテゴリ", "キーワード"])
    for item in data:
        w.writerow([item["id"], item["カテゴリ"], item["キーワード"]])

# flat download list
BASE = "https://ai-costume-gallery.pages.dev/"
jobs = []
for item in data:
    for key, subdir in [("サムネ", "thumbs"), ("画像", "img"), ("原寸", "png")]:
        rel = item[key]  # e.g. thumbs/SPR-0001.webp
        jobs.append({
            "id": item["id"],
            "kind": key,
            "rel": rel,
            "url": BASE + rel,
            "dest": str(ROOT / "images" / rel.replace("/", "\\")),
        })

jobs_path = ROOT / "meta" / "download_jobs.json"
jobs_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"vocab={csv_path} rows={len(data)}")
print(f"jobs={len(jobs)} expected=4221")
print(f"meta_total={meta['total']} cats={len(meta['cats'])}")