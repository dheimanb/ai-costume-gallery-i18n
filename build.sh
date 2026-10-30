#!/usr/bin/env bash
# Cloudflare Pages build: generate the multilingual site, then assemble dist/.
# Inputs: raw/D.json, i18n/dict-unified.csv, i18n/dict-map.json, i18n/ui-strings.csv.
# Output: dist/ (index.html, data/, _headers, robots.txt, thumbs/, img/, png/).
set -euo pipefail
cd "$(dirname "$0")"

GEN="${GEN:-generated}"
DST="${DST:-dist}"

python3 scripts/generate_costume.py \
  --djson raw/D.json \
  --dict i18n/dict-unified.csv \
  --dict-map i18n/dict-map.json \
  --ui i18n/ui-strings.csv \
  --out "$GEN"

python3 "$GEN/verify_costume.py" \
  --site-dir "$GEN" \
  --dict i18n/dict-unified.csv \
  --dict-map i18n/dict-map.json \
  --djson raw/D.json \
  --ui i18n/ui-strings.csv \
  --expect-count 1407

rm -rf "$DST"
mkdir -p "$DST"
cp "$GEN/index.html" "$GEN/_headers" "$DST/"
[ -f "$GEN/robots.txt" ] && cp "$GEN/robots.txt" "$DST/"
cp -R "$GEN/data" "$DST/"
for src in thumbs img png; do
  mkdir -p "$DST/$src"
  cp -R "images/$src/." "$DST/$src/"
done

echo "dist ready: $DST"
du -sh "$DST"
find "$DST" -type f | wc -l
