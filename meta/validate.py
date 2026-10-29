# -*- coding: utf-8 -*-
"""Validate downloaded costume images; refresh manifest statuses; sample dimensions."""
from __future__ import annotations
import json, csv, struct, random
from pathlib import Path
from collections import Counter

ROOT = Path(r"E:\costume-staging")
JOBS = json.loads((ROOT / "meta" / "download_jobs.json").read_text(encoding="utf-8"))
DATA = json.loads((ROOT / "raw" / "D.json").read_text(encoding="utf-8"))

def png_size(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    # IHDR
    if data[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", data[16:24])
    return w, h

def webp_size(data: bytes):
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    # VP8X
    if data[12:16] == b"VP8X":
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return w, h
    # VP8 
    if data[12:16] == b"VP8 ":
        # frame tag + start code
        if len(data) < 30:
            return None
        # lossy VP8: width/height at offset 26 within payload-ish; simpler scan
        # After 'VP8 ' (4) + size(4) = offset 20: 3 byte frame tag, then 0x9d 0x01 0x2a, then 16-bit w/h
        idx = data.find(b"\x9d\x01\x2a")
        if idx < 0 or idx + 7 > len(data):
            return None
        w = struct.unpack("<H", data[idx+3:idx+5])[0] & 0x3FFF
        h = struct.unpack("<H", data[idx+5:idx+7])[0] & 0x3FFF
        return w, h
    # VP8L
    if data[12:16] == b"VP8L":
        b0,b1,b2,b3 = data[21:25]
        w = 1 + (((b1 & 0x3F) << 8) | b0)
        h = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
        return w, h
    return None

rows = []
fails = []
status_counts = Counter()
zero = []
bad_header = []
dims_samples = {"thumbs": [], "img": [], "png": []}

rng = random.Random(42)
sample_ids = set(rng.sample([d["id"] for d in DATA], min(30, len(DATA))))

for job in JOBS:
    dest = Path(job["dest"])
    rel = job["rel"]
    kind_folder = rel.split("/")[0]
    if not dest.is_file():
        row = {"id": job["id"], "filename": rel, "size": 0, "status": "missing"}
        rows.append(row); fails.append(row); status_counts["missing"] += 1
        continue
    size = dest.stat().st_size
    if size == 0:
        row = {"id": job["id"], "filename": rel, "size": 0, "status": "zero"}
        rows.append(row); fails.append(row); status_counts["zero"] += 1; zero.append(rel)
        continue
    data = dest.read_bytes()  # ok for validation; pngs ~1MB avg
    # for large files only read head+tail needed — but 1.5GB total already on disk; reading all into memory per file is heavy.
    # Re-read smarter:
    
# rewrite loop more carefully without loading all pngs fully when not sampling
rows = []
fails = []
status_counts = Counter()
total_bytes = 0

for job in JOBS:
    dest = Path(job["dest"])
    rel = job["rel"]
    folder = rel.split("/")[0]
    if not dest.is_file():
        row = {"id": job["id"], "filename": rel, "size": 0, "status": "missing"}
        rows.append(row); fails.append(row); status_counts["missing"] += 1
        continue
    size = dest.stat().st_size
    total_bytes += size
    if size == 0:
        row = {"id": job["id"], "filename": rel, "size": 0, "status": "zero"}
        rows.append(row); fails.append(row); status_counts["zero"] += 1
        continue
    with dest.open("rb") as f:
        head = f.read(64)
        need_full_head = 4096
        more = f.read(need_full_head - 64)
        head = head + more
    suffix = dest.suffix.lower()
    ok = False
    if suffix == ".webp":
        ok = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    elif suffix == ".png":
        ok = head[:8] == b"\x89PNG\r\n\x1a\n"
    else:
        ok = True
    if not ok:
        row = {"id": job["id"], "filename": rel, "size": size, "status": "bad_header"}
        rows.append(row); fails.append(row); status_counts["bad_header"] += 1
        continue
    # sample dims
    if job["id"] in sample_ids:
        with dest.open("rb") as f:
            blob = f.read(65536) if suffix == ".webp" else f.read(128)
            if suffix == ".png":
                dims = png_size(blob if len(blob) >= 24 else head)
            else:
                # may need more for VP8
                if dims_need := True:
                    with dest.open("rb") as f2:
                        blob = f2.read(min(size, 256*1024))
                dims = webp_size(blob)
        dims_samples.setdefault(folder, []).append({"id": job["id"], "file": rel, "size": size, "dims": dims})
    row = {"id": job["id"], "filename": rel, "size": size, "status": "ok"}
    rows.append(row); status_counts["ok"] += 1

# write manifest + fails
with (ROOT / "meta" / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id", "filename", "size", "status"])
    w.writeheader(); w.writerows(rows)
with (ROOT / "meta" / "missing_or_fail.csv").open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id", "filename", "size", "status"])
    w.writeheader(); w.writerows(fails)

report = {
    "items_extracted": len(DATA),
    "jobs_expected": len(JOBS),
    "status_counts": dict(status_counts),
    "total_bytes": total_bytes,
    "total_MB": round(total_bytes / 1e6, 1),
    "total_GiB": round(total_bytes / (1024**3), 3),
    "per_folder": {},
    "sample_dimensions": dims_samples,
    "fail_count": len(fails),
    "local_model_used": False,
}
for folder in ("thumbs", "img", "png"):
    files = list((ROOT / "images" / folder).glob("*"))
    report["per_folder"][folder] = {
        "count": len(files),
        "bytes": sum(p.stat().st_size for p in files),
    }

(ROOT / "meta" / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("VALIDATION")
print(json.dumps({k: report[k] for k in ["items_extracted","jobs_expected","status_counts","total_MB","total_GiB","fail_count","local_model_used"]}, ensure_ascii=False, indent=2))
print("per_folder", {k: v["count"] for k,v in report["per_folder"].items()})
print("sample_dims_count", {k: len(v) for k,v in dims_samples.items()})
# print a few samples
for folder, samples in dims_samples.items():
    for s in samples[:3]:
        print("sample", folder, s)