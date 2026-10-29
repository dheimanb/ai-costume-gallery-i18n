# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.request import Request, urlopen
import json
jobs = json.loads(Path(r"E:\costume-staging\meta\download_jobs.json").read_text(encoding="utf-8"))
UA = "CostumeArchiveBot/1.0 (non-commercial personal archive; contact: local)"
for job in jobs[:3]:
    req = Request(job["url"], headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    with urlopen(req, timeout=30) as resp:
        data = resp.read(32)
        code = getattr(resp, "status", 200)
    print(f"{job['rel']} status={code} head={data[:12]!r} len_probe_ok")
print("SMOKE_OK")