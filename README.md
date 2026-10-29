# ai-costume-gallery-i18n (staging snapshot)

Private working repo for multilingual localisation (EN / JA / zh-TW / zh-CN) of the AI costume gallery.
Source site: https://ai-costume-gallery.pages.dev/ (original author: ギア / Gia). Non-commercial use; remove on objection.
Spec: dheimanb/agent-handoff #19 (bibi). Collected by script on DESKTOP-9HJ8M88; no model used for extraction/download/validation.

## Layout

```
raw/index.html          site HTML snapshot (unchanged)
raw/D.json              embedded `const D` data, extracted (unchanged)
meta/vocab.csv          id, カテゴリ, キーワード (1407 rows; キーワード is an English keyword string on the source site)
meta/manifest.csv       per-image manifest: id, file, size, status
meta/missing_or_fail.csv  header only = no missing/failed images
meta/validation_report.json  counts / header / decode / dimension checks
meta/*.py               extraction, download and validation scripts
images/thumbs/*.webp    1407 thumbnails (360x540)
images/img/*.webp       1407 display images (1366x2048)
images/png/*.png        1407 originals (1366x2048)
i18n/                   local qwen3:8b drafts (first drafts only, not final)
```

## Counts

- Items: 1407 across 8 categories: 春 215, 夏 254, 秋 244, 冬 253, ランジェリー 199, パーティ 48, 水着 54, セクシー 140
- Images: 4221 (3 x 1407), 0 failures, about 1.42 GiB

## Build (Cloudflare Pages)

This repo holds build sources; the published site is generated at build time, never committed.

- Build command: `./build.sh`
- Output directory: `dist`
- Generator: `scripts/generate_costume.py` (Python stdlib only) — inputs `raw/D.json`, `i18n/dict-unified.csv`, `i18n/dict-map.json`, `i18n/ui-strings.csv`
- `i18n/task1/` holds the reviewed dictionary, category glossary and keyword draft (source of the build inputs).
- `dist/` and `generated/` are build output, gitignored.

Local check: `./build.sh`, then open `dist/index.html` (images are served from `dist/thumbs`, `dist/img`, `dist/png`).
