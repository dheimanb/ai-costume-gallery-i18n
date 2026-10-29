# -*- coding: utf-8 -*-
"""Costume image downloader v3: queue workers, no giant future list."""
from __future__ import annotations
import json, time, csv, sys, os, threading, queue
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, install_opener
from urllib.error import HTTPError

ROOT = Path(r"E:\costume-staging")
JOBS = json.loads((ROOT / "meta" / "download_jobs.json").read_text(encoding="utf-8"))
LOG = ROOT / "meta" / "download.log"
MANIFEST = ROOT / "meta" / "manifest.csv"
FAILS = ROOT / "meta" / "missing_or_fail.csv"
PROGRESS = ROOT / "meta" / "download_progress.json"

WORKERS = 6
UA = "CostumeArchiveBot/1.0 (non-commercial personal archive; contact: local)"
STOP_ON_BLOCK_STREAK = 20
STOP_ON_FAIL_RATE = 0.25
STOP_AFTER = 200

lock = threading.Lock()
state = {
    "ok": 0, "skip": 0, "fail": 0, "bytes": 0,
    "block_streak": 0, "attempted": 0, "done": 0,
    "stop": False, "stop_reason": None,
    "fails": [], "rows": [],
}

def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    with lock:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line); f.flush()

def is_good_existing(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 32:
        return False
    with path.open("rb") as f:
        head = f.read(16)
    if path.suffix.lower() == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if path.suffix.lower() == ".png":
        return head[:8] == b"\x89PNG\r\n\x1a\n"
    return True

def check_header(path_suffix: str, data: bytes) -> bool:
    if len(data) < 32:
        return False
    if path_suffix.lower() == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if path_suffix.lower() == ".png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    return True

def record(row: dict, kind: str) -> None:
    with lock:
        state["rows"].append(row)
        state["done"] += 1
        if kind == "ok":
            state["ok"] += 1
            state["bytes"] += row["size"]
            state["attempted"] += 1
            state["block_streak"] = 0
        elif kind == "skip":
            state["skip"] += 1
        else:
            state["fail"] += 1
            state["attempted"] += 1
            state["fails"].append(row)
            if kind.startswith("http_403") or kind.startswith("http_429") or kind.startswith("http_503"):
                state["block_streak"] += 1
                if state["block_streak"] >= STOP_ON_BLOCK_STREAK:
                    state["stop"] = True
                    state["stop_reason"] = f"block_streak {kind}"
            else:
                state["block_streak"] = 0
            if state["attempted"] >= STOP_AFTER:
                fr = state["fail"] / max(1, state["attempted"])
                if fr >= STOP_ON_FAIL_RATE:
                    state["stop"] = True
                    state["stop_reason"] = f"fail_rate={fr:.2f}"

def save_progress() -> None:
    with lock:
        PROGRESS.write_text(json.dumps({
            "ok": state["ok"], "skip": state["skip"], "fail": state["fail"],
            "bytes": state["bytes"], "attempted": state["attempted"],
            "done": state["done"], "total": len(JOBS),
            "stop": state["stop"], "stop_reason": state["stop_reason"],
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

def worker(q: queue.Queue) -> None:
    while True:
        if state["stop"]:
            return
        try:
            job = q.get_nowait()
        except queue.Empty:
            return
        try:
            dest = Path(job["dest"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            if is_good_existing(dest):
                record({"id": job["id"], "filename": job["rel"], "size": dest.stat().st_size, "status": "skip"}, "skip")
                continue
            req = Request(job["url"], headers={"User-Agent": UA, "Accept": "image/webp,image/png,image/*,*/*"})
            tmp = dest.with_suffix(dest.suffix + ".part")
            try:
                with urlopen(req, timeout=60) as resp:
                    code = getattr(resp, "status", 200)
                    data = resp.read()
                if code in (403, 429, 503):
                    record({"id": job["id"], "filename": job["rel"], "size": 0, "status": f"http_{code}"}, f"http_{code}")
                    continue
                if not check_header(dest.suffix, data):
                    tmp.unlink(missing_ok=True)
                    record({"id": job["id"], "filename": job["rel"], "size": len(data), "status": "bad_header"}, "bad_header")
                    continue
                with tmp.open("wb") as f:
                    f.write(data)
                os.replace(tmp, dest)
                record({"id": job["id"], "filename": job["rel"], "size": len(data), "status": "ok"}, "ok")
            except HTTPError as e:
                tmp.unlink(missing_ok=True)
                record({"id": job["id"], "filename": job["rel"], "size": 0, "status": f"http_{e.code}"}, f"http_{e.code}")
            except Exception as e:
                tmp.unlink(missing_ok=True)
                err = f"{type(e).__name__}:{str(e)[:100]}"
                record({"id": job["id"], "filename": job["rel"], "size": 0, "status": err}, "error")
        finally:
            q.task_done()

def main() -> int:
    log(f"start_v3 jobs={len(JOBS)} workers={WORKERS}")
    q: queue.Queue = queue.Queue()
    for job in JOBS:
        q.put(job)
    threads = [threading.Thread(target=worker, args=(q,), daemon=True) for _ in range(WORKERS)]
    for t in threads:
        t.start()
    t0 = time.monotonic()
    last_done = -1
    stall_ticks = 0
    while any(t.is_alive() for t in threads):
        time.sleep(2)
        save_progress()
        with lock:
            d = state["done"]; ok=state["ok"]; sk=state["skip"]; fl=state["fail"]; b=state["bytes"]; stop=state["stop"]
        if d != last_done:
            last_done = d
            stall_ticks = 0
            elapsed = max(0.1, time.monotonic() - t0)
            log(f"progress {d}/{len(JOBS)} ok={ok} skip={sk} fail={fl} MB={b/1e6:.1f} rate={(ok+sk)/elapsed:.2f}/s")
        else:
            stall_ticks += 1
            if stall_ticks >= 60:  # ~2 min no progress
                state["stop"] = True
                state["stop_reason"] = "stalled_2min"
                log("STALL stop")
                break
        if stop:
            break
    for t in threads:
        t.join(timeout=5)
    save_progress()
    with lock:
        rows = list(state["rows"])
        fails = list(state["fails"])
        have = {(r["id"], r["filename"]) for r in rows}
        for job in JOBS:
            key = (job["id"], job["rel"])
            if key not in have:
                row = {"id": job["id"], "filename": job["rel"], "size": 0, "status": "not_attempted"}
                rows.append(row); fails.append(row)
    with MANIFEST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "filename", "size", "status"])
        w.writeheader(); w.writerows(rows)
    with FAILS.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "filename", "size", "status"])
        w.writeheader(); w.writerows(fails)
    log(f"done ok={state['ok']} skip={state['skip']} fail={state['fail']} stop_reason={state['stop_reason']}")
    return 1 if state["stop"] else 0

if __name__ == "__main__":
    sys.exit(main())