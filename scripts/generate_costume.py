#!/usr/bin/env python3
"""Generate the multilingual costume gallery site from extracted data.

Inputs (all paths are given on the command line; nothing is hardcoded):
  --djson      D.json: the extracted `const D` payload, as a JSON array of
               item objects, or an object holding the array under one of
               items / data / costumes / D / list. A leading `const D =`
               prefix and a trailing semicolon are stripped if present.
               Item fields (exact names, verified against the live site):
               id, カテゴリ, キーワード, サムネ, 画像, 原寸.
               キーワード is a whitespace-separated token string (a list
               is also accepted). Image paths come only from these fields.
  --dict       Dictionary CSV (94 rows expected from the bot delivery).
  --dict-map   JSON file mapping logical fields to the dictionary CSV's
               actual column names, e.g.
               {"key": "key", "ja": "ja", "en": "en",
                "zh-CN": "zh-CN", "zh-TW": "zh-TW", "type": "type"}.
               REQUIRED: column names are never guessed. Missing mapped
               columns are a hard error listing the headers found.
               "type" is optional; when present its values should be
               "category" or "keyword" and lookups are restricted to the
               matching kind. The "key" column must hold exactly the
               value that appears in the data (category value or keyword
               token); a key-semantics mismatch surfaces as 0% coverage
               in verification, never as silent wrong output.
  --ui         UI strings CSV. Columns are resolved by alias:
               id: id, key
               ja: ja, ui_ja, japanese, jp
               en: en, ui_en, english
               zh-CN: zh-CN, zh_CN, ui_zh-CN, ui_zh_CN, sc, simplified
               zh-TW: zh-TW, zh_TW, ui_zh-TW, ui_zh_TW, tc, traditional
               context: context, note
               Missing translations fall back: requested -> en -> ja -> id,
               and every fallback is reported.
  --out        Output directory (site root): receives data/costume-*.json,
               index.html, build.sh, _headers, robots.txt,
               verify_costume.py.
  --default-lang  Default display language (default: en, as decided).
  --repo-url   GitHub repo URL used for the footer/source link
               (default: https://github.com/dheimanb/ai-costume-gallery-i18n).

Outputs keep the input order and ids. Only the Python standard library
is used. Exit 0 on success (warnings allowed), 1 on errors.
"""
import argparse
import csv
import json
import os
import re
import sys

LANGS = ["ja", "en", "zh-CN", "zh-TW"]
DATA_NAMES = {lang: f"data/costume-{lang}.json" for lang in LANGS}

F_ID = "id"
F_CAT = "カテゴリ"
F_KW = "キーワード"
F_THUMB = "サムネ"
F_IMG = "画像"
F_ORIG = "原寸"
REQUIRED_FIELDS = [F_ID, F_CAT, F_KW, F_THUMB, F_IMG, F_ORIG]

# Japanese search synonyms, verbatim from the original site const JA
# (raw/index.html). Query terms are mapped to English keyword tokens
# before matching; unmapped terms match as before.
JA_SEARCH_SYNONYMS = {'アイボリー': 'ivory',
 'イエロー': 'yellow',
 'ウール': 'wool',
 'エプロン': 'apron',
 'オリーブ': 'olive',
 'オレンジ': 'orange',
 'カチューシャ': 'headband',
 'カーキ': 'khaki',
 'カーディガン': 'cardigan',
 'キャミソール': 'camisole',
 'クリーム': 'cream',
 'グリーン': 'green',
 'グレー': 'grey',
 'コルセット': 'corset',
 'コーデュロイ': 'corduroy',
 'コート': 'coat',
 'ゴールド': 'gold',
 'サテン': 'satin',
 'サングラス': 'sunglasses',
 'サンダル': 'sandals',
 'シフォン': 'chiffon',
 'シャツ': 'shirt',
 'ショーツ': 'briefs',
 'ショートパンツ': 'shorts',
 'シルバー': 'silver',
 'ジャケット': 'jacket',
 'ジーンズ': 'jeans',
 'スエード': 'suede',
 'スカート': 'skirt',
 'スカーフ': 'scarf',
 'ストッキング': 'stockings',
 'スニーカー': 'sneakers',
 'セーター': 'sweater',
 'ソックス': 'socks',
 'タイツ': 'tights',
 'タートルネック': 'turtleneck',
 'チュール': 'tulle',
 'チョーカー': 'choker',
 'デニム': 'denim',
 'トート': 'tote',
 'ドット': 'polka-dot',
 'ドレス': 'dress',
 'ニット': 'knit',
 'ニット帽': 'beanie',
 'ネイビー': 'navy',
 'ネックレス': 'necklace',
 'ハット': 'hat',
 'バッグ': 'bag',
 'パンツ': 'pants',
 'パンプス': 'pumps',
 'パーカー': 'hoodie',
 'パープル': 'purple',
 'ヒール': 'heels',
 'ビキニ': 'bikini',
 'ピンク': 'pink',
 'ファー': 'fur',
 'フリル': 'frill',
 'ブラ': 'bra',
 'ブラウス': 'blouse',
 'ブラウン': 'brown',
 'ブラック': 'black',
 'ブルー': 'blue',
 'ブーツ': 'boots',
 'プリーツ': 'pleated',
 'ベスト': 'vest',
 'ベルト': 'belt',
 'ベルベット': 'velvet',
 'ベレー帽': 'beret',
 'ベージュ': 'beige',
 'ホワイト': 'white',
 'ボルドー': 'burgundy',
 'マキシ': 'maxi',
 'マフラー': 'muffler',
 'ミディ': 'midi',
 'ミニ': 'mini',
 'ミント': 'mint',
 'メッシュ': 'mesh',
 'ラベンダー': 'lavender',
 'リボン': 'ribbon',
 'レザー': 'leather',
 'レッド': 'red',
 'レース': 'lace',
 'ローファー': 'loafers',
 'ローブ': 'robe',
 'ワンピース': 'dress',
 '帽子': 'hat',
 '手袋': 'gloves',
 '水玉': 'polka-dot',
 '水着': 'swimsuit',
 '灰': 'grey',
 '白': 'white',
 '紫': 'purple',
 '紺': 'navy',
 '緑': 'green',
 '花柄': 'floral',
 '茶': 'brown',
 '赤': 'red',
 '金': 'gold',
 '銀': 'silver',
 '青': 'blue',
 '革': 'leather',
 '靴下': 'socks',
 '黄': 'yellow',
 '黒': 'black'}

UI_ALIASES = {
    "id": ["id", "key"],
    "ja": ["ja", "ui_ja", "japanese", "jp"],
    "en": ["en", "ui_en", "english"],
    "zh-CN": ["zh-CN", "zh_CN", "ui_zh-CN", "ui_zh_CN", "sc", "simplified", "zh-Hans"],
    "zh-TW": ["zh-TW", "zh_TW", "ui_zh-TW", "ui_zh_TW", "tc", "traditional", "zh-Hant"],
    "context": ["context", "note"],
}

SOURCE_URL = "https://ai-costume-gallery.pages.dev/"
CREATOR_URL = "https://x.com/giaaibusi"


class GenError(Exception):
    pass


def fail(msg):
    raise GenError(msg)


def load_djson(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read().strip()
    if text.startswith("const"):
        eq = text.find("=")
        if eq == -1:
            fail(f"{path}: starts with 'const' but has no '='; cannot parse as D payload")
        text = text[eq + 1:].strip()
    if text.endswith(";"):
        text = text[:-1].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        fail(f"{path}: not valid JSON (after const-prefix stripping): {e}")
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = None
        for key in ("items", "data", "costumes", "D", "list"):
            if isinstance(data.get(key), list):
                items = data[key]
                break
        if items is None:
            fail(f"{path}: object payload without an array under items/data/costumes/D/list; keys found: {sorted(data.keys())}")
    else:
        fail(f"{path}: payload must be a JSON array or an object holding one; got {type(data).__name__}")
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            fail(f"{path}: item {i} is not an object: {str(it)[:80]}")
    return items


def load_dict(path, map_path, warnings):
    with open(map_path, "r", encoding="utf-8-sig") as f:
        try:
            mapping = json.load(f)
        except json.JSONDecodeError as e:
            fail(f"{map_path}: invalid JSON: {e}")
    for logical in ("key", "ja", "en", "zh-CN", "zh-TW"):
        if logical not in mapping:
            fail(f"{map_path}: missing logical field {logical!r}; mapping must define key, ja, en, zh-CN, zh-TW (and optionally type)")
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        missing = [m for m in mapping.values() if m and m not in headers]
        if missing:
            fail(f"{path}: dictionary CSV is missing mapped columns {missing}; headers found: {headers}")
        lookup = {}
        seen = {}
        for row_no, row in enumerate(reader, start=2):
            key = (row.get(mapping["key"]) or "").strip()
            if not key:
                warnings.append(f"dict row {row_no}: empty key, skipped")
                continue
            if key in seen:
                fail(f"{path}: duplicate dictionary key {key!r} (rows {seen[key]} and {row_no}); keys must be unique")
            seen[key] = row_no
            entry = {"__type__": ""}
            if mapping.get("type"):
                entry["__type__"] = (row.get(mapping["type"]) or "").strip().lower()
                if entry["__type__"] not in ("", "category", "keyword"):
                    warnings.append(f"dict row {row_no} (key {key!r}): unexpected type {entry['__type__']!r}, expected 'category'/'keyword'")
            for lang in LANGS:
                entry[lang] = (row.get(mapping[lang]) or "").strip()
            lookup[key] = entry
    return lookup


def resolve_col(headers, logical):
    for cand in UI_ALIASES[logical]:
        if cand in headers:
            return cand
    return None


def load_ui(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        cols = {}
        for logical in ("id", "ja", "en", "zh-CN", "zh-TW", "context"):
            cols[logical] = resolve_col(headers, logical)
        if not cols["id"]:
            fail(f"{path}: UI CSV has no id column; headers found: {headers}")
        strings = {}
        for row_no, row in enumerate(reader, start=2):
            sid = (row.get(cols["id"]) or "").strip()
            if not sid:
                continue
            if sid in strings:
                fail(f"{path}: duplicate UI string id {sid!r} (row {row_no})")
            strings[sid] = {lang: ((row.get(cols[lang]) or "").strip() if cols[lang] else "") for lang in LANGS}
    return strings


def resolve_ui(strings):
    """Apply fallback chain requested -> en -> ja -> id. Returns (ui, fallbacks)."""
    ui = {lang: {} for lang in LANGS}
    fallbacks = []
    for sid, vals in strings.items():
        for lang in LANGS:
            val = vals.get(lang) or ""
            src = lang
            if not val:
                val = vals.get("en") or ""
                src = "en"
            if not val:
                val = vals.get("ja") or ""
                src = "ja"
            if not val:
                val = sid
                src = "id"
            if src != lang:
                fallbacks.append((sid, lang, src))
            ui[lang][sid] = val
    return ui, fallbacks


def split_keywords(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t for t in re.split(r"[\s,]+", str(raw).strip()) if t]


def translate(lookup, term, lang, kind, used):
    entry = lookup.get(term)
    if entry is None:
        return None
    rtype = entry.get("__type__") or ""
    if rtype and rtype != kind:
        return None
    val = entry.get(lang) or ""
    if not val:
        return None
    used.add(term)
    return val


def build_data(items, lookup, warnings):
    per_lang = {lang: [] for lang in LANGS}
    untranslated = set()
    used = set()
    seen_ids = set()
    for i, raw in enumerate(items):
        missing = [f for f in (F_ID, F_THUMB, F_IMG, F_ORIG) if not str(raw.get(f) or "").strip()]
        if missing:
            fail(f"item {i}: missing required fields {missing}; id={str(raw.get(F_ID))[:40]!r}")
        item_id = str(raw[F_ID]).strip()
        if item_id in seen_ids:
            fail(f"duplicate id {item_id!r} at item {i}")
        seen_ids.add(item_id)
        cat = str(raw.get(F_CAT) or "").strip()
        if not cat:
            warnings.append(f"item {i} ({item_id}): empty category")
        tokens = split_keywords(raw.get(F_KW))
        if not tokens:
            warnings.append(f"item {i} ({item_id}): no keywords")
        for lang in LANGS:
            cat_t = translate(lookup, cat, lang, "category", used) if cat else ""
            if cat and cat_t is None:
                untranslated.add((cat, "category", lang))
                cat_t = cat
            kws_t = []
            for tok in tokens:
                t = translate(lookup, tok, lang, "keyword", used)
                if t is None:
                    untranslated.add((tok, "keyword", lang))
                    t = tok
                kws_t.append(t)
            search = " ".join([item_id, cat_t] + kws_t).lower()
            per_lang[lang].append({
                "id": item_id,
                "category": cat_t,
                "keywords": kws_t,
                "thumb": str(raw[F_THUMB]).strip(),
                "image": str(raw[F_IMG]).strip(),
                "orig": str(raw[F_ORIG]).strip(),
                "search": search,
            })
    unused = sorted(set(lookup) - used)
    return per_lang, untranslated, unused

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light">
<title>Costume Collection COSTUME-DB-01</title>
<meta name="description" content="Costume reference gallery: 1,407 outfits across 8 categories, with keyword tags and full-size images.">
<!-- TODO(domain): replace relative canonical/og URLs with absolute URLs once the production domain is decided. -->
<link rel="canonical" href="/">
<meta property="og:type" content="website">
<meta property="og:title" content="Costume Collection COSTUME-DB-01">
<meta property="og:description" content="Costume reference gallery: 1,407 outfits across 8 categories, with keyword tags and full-size images.">
<meta property="og:url" content="/">
<meta name="twitter:card" content="summary_large_image">
<style>
:root{--bg:#f5f6fa;--surface:#fff;--line:#e4e5f0;--line-strong:#cfd0e0;--text:#1d2130;--text-2:#62667a;--accent:#5b5bd6;--accent-dark:#4646ad;--accent-soft:#ececfb;--radius:14px}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Hiragino Sans","Noto Sans JP","Noto Sans TC",sans-serif;line-height:1.55}
a{color:var(--accent-dark)}
.shell{max-width:1240px;margin:0 auto;padding:0 20px}
.site-header{background:var(--surface);border-bottom:1px solid var(--line)}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 0}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--text)}
.brand-mark{width:38px;height:38px;border-radius:11px;background:var(--accent);color:#fff;display:grid;place-items:center;font-weight:800}
.brand-copy{display:flex;flex-direction:column;line-height:1.2}
.brand-copy strong{font-size:17px;letter-spacing:.02em}
.brand-copy span{font-size:11px;color:var(--text-2);letter-spacing:.12em;text-transform:uppercase}
.top-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.segmented{display:inline-flex;border:1px solid var(--line-strong);border-radius:11px;overflow:hidden;background:var(--surface)}
.segmented button{border:0;background:transparent;padding:8px 12px;font:inherit;font-size:13px;font-weight:600;cursor:pointer;color:var(--text-2)}
.segmented button[aria-pressed="true"]{background:var(--accent);color:#fff}
.action-btn{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 12px;border:1px solid var(--line);border-radius:9px;background:var(--surface);color:var(--text-2);font-size:13px;font-weight:600;text-decoration:none;cursor:pointer}
.action-btn:hover{border-color:var(--accent);color:var(--accent)}
.hero{display:grid;grid-template-columns:1fr auto;gap:24px;padding:26px 0 30px;align-items:end}
.eyebrow{margin:0 0 8px;color:var(--accent-dark);font-size:12px;font-weight:800;letter-spacing:.14em}
.hero h1{margin:0;font-size:34px;line-height:1.15;letter-spacing:-.01em}
.hero-tagline{display:block;font-size:16px;font-weight:600;color:var(--text-2);margin-top:6px}
.hero-desc{margin:12px 0 0;color:var(--text-2);max-width:640px}
.hero-stats{display:flex;gap:26px}
.stat strong{display:block;font-size:26px}
.stat span{font-size:12px;color:var(--text-2)}
.controls{position:sticky;top:0;z-index:30;background:rgba(245,246,250,.94);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.controls-inner{padding:14px 0}
.cat-chips{display:flex;gap:8px;flex-wrap:wrap}
.chip{border:1px solid var(--line-strong);background:var(--surface);border-radius:99px;padding:7px 13px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.chip .count{opacity:.65;font-weight:500;margin-left:4px}
.search-row{display:flex;gap:10px;margin-top:12px;align-items:center}
.search-box{flex:1;display:flex;align-items:center;gap:8px;border:1px solid var(--line-strong);border-radius:11px;background:var(--surface);padding:0 12px;height:44px}
.search-box input{flex:1;border:0;outline:0;font:inherit;font-size:14px;background:transparent;min-width:0}
.search-clear{border:0;background:transparent;cursor:pointer;color:var(--text-2);font-size:16px;padding:4px}
.reset-btn{height:44px;padding:0 14px;border:1px solid var(--line);border-radius:11px;background:var(--surface);font:inherit;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
.tag-row{margin-top:12px}
.tag-wrap{padding:14px 0 4px}
.tag-toggle{display:none;width:100%;align-items:center;justify-content:space-between;border:1px solid var(--line-strong);border-radius:11px;background:var(--surface);padding:10px 14px;font:inherit;font-size:13px;font-weight:700;cursor:pointer;color:inherit}
.tag-chev{width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;border-top:6px solid currentColor;transition:transform .15s;flex:none}
.tag-wrap.open .tag-chev{transform:rotate(180deg)}
.tag-label{font-size:11px;font-weight:700;color:var(--text-2);display:block;margin-bottom:7px}
.tag-cloud{display:flex;gap:7px;flex-wrap:wrap}
.tag{border:1px solid #dcdcf5;background:var(--accent-soft);color:var(--accent-dark);border-radius:8px;padding:5px 10px;font:inherit;font-size:12px;font-weight:600;cursor:pointer}
.tag[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.tag .count{opacity:.65;font-weight:500;margin-left:3px}
.active-filters{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}
.active-filters:empty{display:none}
.filter-chip{height:28px;padding:0 9px;border:1px solid #dcdcf5;border-radius:8px;background:var(--accent-soft);color:var(--accent-dark);display:inline-flex;align-items:center;gap:6px;font-size:12px;cursor:pointer}
.filter-chip::after{content:"\00d7";font-size:15px;line-height:1}
main{padding:22px 0 40px}
.result-count{color:var(--text-2);font-size:13px;margin:0 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;cursor:pointer;text-align:left;padding:0;font:inherit;color:inherit;width:100%}
.card img{width:100%;aspect-ratio:2/3;object-fit:cover;display:block;background:#e8e9f2}
.card-body{padding:10px 12px 12px}
.card-id{font-family:ui-monospace,monospace;font-size:11px;color:var(--text-2)}
.card-cat{display:inline-block;margin-top:5px;font-size:11px;font-weight:700;color:var(--accent-dark);background:var(--accent-soft);border-radius:6px;padding:2px 7px}
.card-tags{margin-top:8px;display:flex;flex-wrap:wrap;gap:5px}
.card-tags span{font-size:11px;border:1px solid var(--line);border-radius:6px;padding:1px 6px;color:var(--text-2)}
.empty{border:1px dashed var(--line-strong);border-radius:var(--radius);padding:34px;text-align:center;color:var(--text-2)}
.load-more{display:block;margin:22px auto 0;height:46px;padding:0 26px;border:1px solid var(--line-strong);border-radius:11px;background:var(--surface);font:inherit;font-size:14px;font-weight:700;cursor:pointer}
.site-footer{border-top:1px solid var(--line);background:var(--surface);padding:28px 0 34px}
.footer-inner{display:flex;justify-content:space-between;align-items:flex-start;gap:30px}
.footer-copy{max-width:720px;color:var(--text-2);font-size:12px;line-height:1.9}
.footer-copy p{margin:0 0 5px}
.footer-links{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end}
.footer-links a{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 12px;border:1px solid var(--line);border-radius:9px;text-decoration:none;color:var(--text-2);font-size:12px;font-weight:600}
.viewer{position:fixed;inset:0;z-index:100;display:grid;place-items:center;padding:26px;background:rgba(15,18,28,.76)}
.viewer[hidden]{display:none}
.viewer-panel{background:var(--surface);border-radius:16px;max-width:1020px;width:100%;max-height:calc(100vh - 52px);overflow:auto;display:grid;grid-template-columns:1.25fr 1fr;position:relative}
.viewer-close{position:absolute;top:10px;right:10px;z-index:2;width:36px;height:36px;border-radius:50%;border:1px solid var(--line);background:var(--surface);cursor:pointer;font-size:16px}
.viewer-stage{background:#171a26;display:grid;place-items:center;min-height:320px;position:relative}
.viewer-stage img{max-width:100%;max-height:calc(100vh - 52px);object-fit:contain;display:block}
.viewer-nav{position:absolute;top:50%;transform:translateY(-50%);width:40px;height:40px;border-radius:50%;border:0;background:rgba(255,255,255,.9);cursor:pointer;font-size:18px}
.viewer-nav.prev{left:10px}
.viewer-nav.next{right:10px}
.viewer-side{padding:22px}
.viewer-side h2{margin:4px 0 10px;font-size:20px}
.viewer-id{font-family:ui-monospace,monospace;font-size:12px;word-break:break-all}
.copy-btn{margin-left:8px;border:1px solid var(--line);border-radius:7px;background:var(--surface);padding:4px 9px;font:inherit;font-size:12px;cursor:pointer}
.viewer-meta{margin:14px 0;font-size:13px;color:var(--text-2)}
.viewer-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.download-stack{display:grid;gap:8px;margin-top:18px}
.download-btn,.open-btn{display:flex;align-items:center;justify-content:center;gap:7px;height:42px;border-radius:10px;text-decoration:none;font-weight:700;font-size:14px}
.download-btn{background:var(--accent);color:#fff}
.open-btn{border:1px solid var(--line-strong);color:var(--text)}
.keyboard-help{margin-top:16px;font-size:12px;color:var(--text-2)}
dialog.info-dialog{border:1px solid var(--line);border-radius:14px;max-width:560px;width:calc(100% - 40px);padding:0}
dialog.info-dialog::backdrop{background:rgba(15,18,28,.55)}
.info-head{display:flex;justify-content:space-between;align-items:center;padding:16px 18px;border-bottom:1px solid var(--line)}
.info-head h2{margin:0;font-size:17px}
.info-close{border:0;background:transparent;cursor:pointer;font-size:16px}
.info-content{padding:18px;line-height:1.8;white-space:pre-line}
@media (max-width:900px){.hero{grid-template-columns:1fr}.viewer-panel{grid-template-columns:1fr}.footer-inner{display:block}.footer-links{justify-content:flex-start;margin-top:16px}}
@media (max-width:640px){.hero h1{font-size:27px}.hero-stats{gap:18px}.search-row{flex-wrap:wrap}.tag-toggle{display:flex}.tag-wrap .tag-row{display:none}.tag-wrap.open .tag-row{display:block}}
</style>
</head>
<body>
<header class="site-header">
  <div class="shell topbar">
    <a class="brand" href="./" aria-label="Costume Collection home">
      <span class="brand-mark">C</span>
      <span class="brand-copy"><strong>COSTUME-DB-01</strong><span data-i18n="site_title">Costume Collection</span></span>
    </a>
    <nav class="top-actions" aria-label="Help and sources">
      <div class="segmented" id="langSwitch" role="group" aria-label="Language">
        <button type="button" data-lang="en" aria-pressed="true">English</button><button type="button" data-lang="ja" aria-pressed="false">日本語</button><button type="button" data-lang="zh-CN" aria-pressed="false">简体中文</button><button type="button" data-lang="zh-TW" aria-pressed="false">繁體中文</button>
      </div>
      <button class="action-btn" type="button" data-info="guide"><span data-i18n="guide_title">How to use</span></button>
      <button class="action-btn" type="button" data-info="notice"><span data-i18n="notice_title">Notes</span></button>
      <a class="action-btn" href="__CREATOR_URL__" target="_blank" rel="noopener noreferrer"><span data-i18n="creator_label">Creator: Gia</span></a>
      <a class="action-btn" href="__SOURCE_URL__" target="_blank" rel="noopener noreferrer"><span data-i18n="openchat_join">Join the open chat</span></a>
    </nav>
  </div>
  <div class="shell hero">
    <div>
      <p class="eyebrow">COSTUME-DB-01</p>
      <h1><span data-i18n="site_title">Costume Collection</span><span class="hero-tagline" data-i18n="hero_tagline">Find every outfit for your next render</span></h1>
      <p class="hero-desc" data-i18n="openchat_note">Learn effective ways to use this collection (including uncensored-AI use) in the open chat.</p>
    </div>
    <div class="hero-stats" aria-label="Collection statistics">
      <div class="stat"><strong id="statItems">0</strong><span data-i18n="stats_items">items</span></div>
      <div class="stat"><strong id="statCats">0</strong><span data-i18n="stats_categories">categories</span></div>
      <div class="stat"><strong id="statTags">0</strong><span data-i18n="stats_keywords">keywords</span></div>
    </div>
  </div>
</header>

<section class="controls" aria-label="Gallery filters">
  <div class="shell controls-inner">
    <div class="cat-chips" id="catChips" role="group" aria-label="Categories"></div>
    <div class="search-row">
      <label class="search-box">
        <input id="searchInput" type="search" data-i18n-ph="search_placeholder" placeholder="Search by ID / category / keyword" autocomplete="off">
        <button class="search-clear" id="searchClear" type="button" aria-label="Clear search" hidden>&times;</button>
      </label>
      <button class="reset-btn" id="resetFilters" type="button" data-i18n="reset_filters">Reset filters</button>
    </div>
    <div class="active-filters" id="activeFilters"></div>
  </div>
</section>

<div class="shell tag-wrap" id="tagWrap">
  <button type="button" class="tag-toggle" id="tagToggle" aria-expanded="false" aria-controls="tagCloud"><span data-i18n="filter_tags_label">Keyword tags</span><span class="tag-chev" aria-hidden="true"></span></button>
  <div class="tag-row">
    <span class="tag-label" data-i18n="filter_tags_label">Keyword tags</span>
    <div class="tag-cloud" id="tagCloud"></div>
  </div>
</div>

<main class="shell">
  <p class="result-count" id="resultCount"></p>
  <div class="grid" id="grid"></div>
  <div class="empty" id="noResults" hidden><span data-i18n="no_results">No items match the current filters.</span></div>
  <button class="load-more" id="loadMore" type="button" hidden><span data-i18n="load_more">Load more</span></button>
</main>

<footer class="site-footer">
  <div class="shell footer-inner">
    <div class="footer-copy">
      <p data-i18n="footer_attr_1">Images and source data are copyright of the original author, Gia.</p>
      <p data-i18n="footer_attr_2">This site is a non-commercial mirror. Content will be removed immediately upon objection from the original author.</p>
      <p><span data-i18n="footer_source">Source: ai-costume-gallery.pages.dev</span> &middot; <a href="__SOURCE_URL__" target="_blank" rel="noopener noreferrer">ai-costume-gallery.pages.dev</a></p>
    </div>
    <div class="footer-links">
      <a href="__REPO_URL__" target="_blank" rel="noopener noreferrer"><span data-i18n="footer_github">GitHub source</span></a>
      <a href="__CREATOR_URL__" target="_blank" rel="noopener noreferrer">@giaaibusi</a>
    </div>
  </div>
</footer>

<div class="viewer" id="viewer" role="dialog" aria-modal="true" aria-labelledby="viewerTitle" hidden>
  <section class="viewer-panel">
    <button class="viewer-close" id="viewerClose" type="button" data-i18n-aria="viewer_close" aria-label="Close viewer">&times;</button>
    <div class="viewer-stage">
      <img id="viewerImage" alt="">
      <button class="viewer-nav prev" id="viewerPrev" type="button" data-i18n-aria="viewer_prev" aria-label="Previous item">&#8249;</button>
      <button class="viewer-nav next" id="viewerNext" type="button" data-i18n-aria="viewer_next" aria-label="Next item">&#8250;</button>
    </div>
    <aside class="viewer-side">
      <div><span id="viewerPosition"></span></div>
      <h2 id="viewerTitle"></h2>
      <div><code class="viewer-id" id="viewerId"></code><button class="copy-btn" id="copyId" type="button" data-i18n="viewer_copy_id">Copy ID</button></div>
      <div class="viewer-meta"><span id="viewerCat"></span><div class="viewer-tags" id="viewerTags"></div></div>
      <div class="download-stack">
        <a class="download-btn" id="downloadOrig" href="#" download data-i18n="viewer_download_orig">Download full size</a>
        <a class="open-btn" id="openOrig" href="#" target="_blank" rel="noopener noreferrer" data-i18n="viewer_open_new">Open in new tab</a>
      </div>
      <div class="keyboard-help">Esc &middot; &larr; &rarr;</div>
    </aside>
  </section>
</div>

<dialog class="info-dialog" id="infoDialog">
  <div class="info-head"><h2 id="infoTitle"></h2><button class="info-close" id="infoClose" type="button" aria-label="Close">&times;</button></div>
  <div class="info-content" id="infoContent"></div>
</dialog>

<script>
(() => {
'use strict';
const UI = __UI_JSON__;
const JA_SYN = __JA_SYN_JSON__;
const CATS = __CATS_JSON__;
const CAT_DISPLAY = __CAT_DISPLAY_JSON__;
const LANGS = {
  en: { file: 'data/costume-en.json', locale: 'en' },
  ja: { file: 'data/costume-ja.json', locale: 'ja' },
  'zh-CN': { file: 'data/costume-zh-CN.json', locale: 'zh-CN' },
  'zh-TW': { file: 'data/costume-zh-TW.json', locale: 'zh-TW' }
};
const DEFAULT_LANG = '__DEFAULT_LANG__';
const PAGE_SIZE = 60;
const state = { lang: DEFAULT_LANG, category: '', tags: new Set(), query: '', shown: PAGE_SIZE };
let DATA = [];
let currentList = [];
const $ = s => document.querySelector(s);
const grid = $('#grid');
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const t = id => (UI[state.lang] && UI[state.lang][id]) || UI.en[id] || id;
const fmt = n => Number(n).toLocaleString(LANGS[state.lang].locale);

function applyStrings() {
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.getAttribute('data-i18n')); });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.getAttribute('data-i18n-ph')); });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria'))); });
  document.documentElement.lang = LANGS[state.lang].locale;
  document.title = t('site_title') + ' ' + t('site_code');
}

function catLabel(key, lang) {
  const c = CATS.find(x => x.key === key);
  return c ? (c.label[lang] || c.label.en || c.key) : key;
}

function catDisplay(key, lang) {
  const d = CAT_DISPLAY[key];
  return (d && (d[lang] || d.en)) || catLabel(key, lang);
}

function catDisplayForValue(value, lang) {
  const c = CATS.find(x => x.label[lang] === value);
  return c ? catDisplay(c.key, lang) : value;
}

function renderCats() {
  const wrap = $('#catChips');
  const counts = new Map();
  DATA.forEach(it => { counts.set(it.category, (counts.get(it.category) || 0) + 1); });
  let html = '<button type="button" class="chip" data-cat="" aria-pressed="' + (state.category === '') + '">' + esc(t('filter_all')) + ' <span class="count">' + fmt(DATA.length) + '</span></button>';
  CATS.forEach(c => {
    const label = catLabel(c.key, state.lang);
    const n = counts.get(label) || 0;
    if (!n) return;
    html += '<button type="button" class="chip" data-cat="' + esc(c.key) + '" aria-pressed="' + (state.category === c.key) + '">' + esc(catDisplay(c.key, state.lang)) + ' <span class="count">' + fmt(n) + '</span></button>';
  });
  wrap.innerHTML = html;
  wrap.querySelectorAll('.chip').forEach(btn => btn.addEventListener('click', () => {
    state.category = btn.getAttribute('data-cat');
    state.shown = PAGE_SIZE;
    renderAll();
  }));
}

function baseFiltered() {
  const q = state.query.trim().toLowerCase();
  const qtokens = q ? q.split(/\s+/) : [];
  return DATA.filter(it => {
    if (state.category && it.category !== catLabel(state.category, state.lang)) return false;
    if (qtokens.length && !qtokens.every(tok => it.search.includes(tok) || (JA_SYN[tok] && it.search.includes(JA_SYN[tok])))) return false;
    return true;
  });
}

function filtered() {
  const base = baseFiltered();
  if (!state.tags.size) return base;
  return base.filter(it => [...state.tags].every(tag => it.keywords.includes(tag)));
}

function renderTags() {
  const counts = new Map();
  baseFiltered().forEach(it => it.keywords.forEach(k => counts.set(k, (counts.get(k) || 0) + 1)));
  const entries = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  $('#tagCloud').innerHTML = entries.map(([k, n]) =>
    '<button type="button" class="tag" data-tag="' + esc(k) + '" aria-pressed="' + state.tags.has(k) + '">' + esc(k) + ' <span class="count">' + fmt(n) + '</span></button>'
  ).join('');
  document.querySelectorAll('#tagCloud .tag').forEach(btn => btn.addEventListener('click', () => {
    const tag = btn.getAttribute('data-tag');
    if (state.tags.has(tag)) state.tags.delete(tag); else state.tags.add(tag);
    state.shown = PAGE_SIZE;
    renderAll();
  }));
}

function renderActive() {
  const chips = [];
  if (state.category) chips.push({ label: catDisplay(state.category, state.lang), clear: () => { state.category = ''; } });
  state.tags.forEach(tag => chips.push({ label: tag, clear: () => { state.tags.delete(tag); } }));
  if (state.query.trim()) chips.push({ label: '"' + state.query.trim() + '"', clear: () => { state.query = ''; $('#searchInput').value = ''; } });
  const wrap = $('#activeFilters');
  wrap.innerHTML = chips.map((c, i) => '<button type="button" class="filter-chip" data-i="' + i + '">' + esc(c.label) + '</button>').join('');
  wrap.querySelectorAll('.filter-chip').forEach(btn => btn.addEventListener('click', () => {
    chips[Number(btn.getAttribute('data-i'))].clear();
    state.shown = PAGE_SIZE;
    renderAll();
  }));
}

function renderGrid() {
  const list = currentList.slice(0, state.shown);
  grid.innerHTML = list.map((it, i) =>
    '<button type="button" class="card" data-i="' + i + '">' +
    '<img loading="lazy" src="' + esc(it.thumb) + '" alt="' + esc(it.id) + '">' +
    '<span class="card-body" style="display:block"><span class="card-id">' + esc(it.id) + '</span><br>' +
    '<span class="card-cat">' + esc(catDisplayForValue(it.category, state.lang)) + '</span>' +
    '<span class="card-tags">' + it.keywords.map(k => '<span>' + esc(k) + '</span>').join('') + '</span></span></button>'
  ).join('');
  grid.querySelectorAll('.card').forEach(btn => btn.addEventListener('click', () => openViewer(Number(btn.getAttribute('data-i')))));
  $('#noResults').hidden = currentList.length !== 0;
  $('#loadMore').hidden = currentList.length <= state.shown;
  $('#resultCount').textContent = t('results_count').replace('{n}', fmt(currentList.length));
}

function renderStats() {
  $('#statItems').textContent = fmt(DATA.length);
  $('#statCats').textContent = fmt(new Set(DATA.map(it => it.category)).size);
  $('#statTags').textContent = fmt(new Set(DATA.flatMap(it => it.keywords)).size);
}

function renderAll() {
  currentList = filtered();
  renderCats();
  renderTags();
  renderActive();
  renderStats();
  renderGrid();
}

const viewer = { index: 0, token: 0 };
function openViewer(i) {
  viewer.index = i;
  const it = currentList[i];
  if (!it) return;
  viewer.token += 1;
  const token = viewer.token;
  const img = $('#viewerImage');
  img.alt = it.id;
  img.src = it.image;
  $('#viewerTitle').textContent = it.id;
  $('#viewerId').textContent = it.id;
  $('#viewerPosition').textContent = (i + 1) + ' / ' + currentList.length;
  $('#viewerCat').textContent = catDisplayForValue(it.category, state.lang);
  $('#viewerTags').innerHTML = it.keywords.map(k => '<button type="button" class="tag" data-tag="' + esc(k) + '">' + esc(k) + '</button>').join('');
  $('#viewerTags').querySelectorAll('.tag').forEach(btn => btn.addEventListener('click', () => {
    state.tags.add(btn.getAttribute('data-tag'));
    closeViewer();
    state.shown = PAGE_SIZE;
    renderAll();
  }));
  const dl = $('#downloadOrig');
  dl.href = it.orig;
  dl.setAttribute('download', it.id);
  $('#openOrig').href = it.orig;
  $('#viewer').hidden = false;
  document.body.style.overflow = 'hidden';
  return token;
}
function closeViewer() {
  $('#viewer').hidden = true;
  document.body.style.overflow = '';
}
function stepViewer(d) {
  if (!currentList.length) return;
  openViewer((viewer.index + d + currentList.length) % currentList.length);
}
$('#viewerClose').addEventListener('click', closeViewer);
$('#viewerPrev').addEventListener('click', () => stepViewer(-1));
$('#viewerNext').addEventListener('click', () => stepViewer(1));
$('#viewer').addEventListener('click', e => { if (e.target.id === 'viewer') closeViewer(); });
$('#copyId').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText($('#viewerId').textContent); $('#copyId').textContent = t('viewer_id_copied'); }
  catch (e) { /* clipboard unavailable; selection fallback */ const r = document.createRange(); r.selectNodeContents($('#viewerId')); const s = getSelection(); s.removeAllRanges(); s.addRange(r); }
});
document.addEventListener('keydown', e => {
  if ($('#viewer').hidden) return;
  if (e.key === 'Escape') closeViewer();
  if (e.key === 'ArrowLeft') stepViewer(-1);
  if (e.key === 'ArrowRight') stepViewer(1);
});

function openInfo(kind) {
  $('#infoTitle').textContent = t(kind === 'guide' ? 'guide_title' : 'notice_title');
  $('#infoContent').textContent = t(kind === 'guide' ? 'guide_body' : 'notice_body');
  $('#infoDialog').showModal();
}
document.querySelectorAll('[data-info]').forEach(btn => btn.addEventListener('click', () => openInfo(btn.getAttribute('data-info'))));
$('#infoClose').addEventListener('click', () => $('#infoDialog').close());

$('#searchInput').addEventListener('input', e => {
  state.query = e.target.value;
  $('#searchClear').hidden = !state.query;
  state.shown = PAGE_SIZE;
  renderAll();
});
$('#searchClear').addEventListener('click', () => {
  $('#searchInput').value = '';
  state.query = '';
  $('#searchClear').hidden = true;
  state.shown = PAGE_SIZE;
  renderAll();
});
document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== $('#searchInput') && $('#viewer').hidden) {
    e.preventDefault();
    $('#searchInput').focus();
  }
});
$('#resetFilters').addEventListener('click', () => {
  state.category = '';
  state.tags.clear();
  state.query = '';
  $('#searchInput').value = '';
  $('#searchClear').hidden = true;
  state.shown = PAGE_SIZE;
  renderAll();
});
$('#tagToggle').addEventListener('click', () => {
  const open = $('#tagWrap').classList.toggle('open');
  $('#tagToggle').setAttribute('aria-expanded', String(open));
});
$('#loadMore').addEventListener('click', () => { state.shown += PAGE_SIZE; renderGrid(); });

document.querySelectorAll('#langSwitch button').forEach(btn => btn.addEventListener('click', () => loadLang(btn.getAttribute('data-lang'))));

async function loadLang(lang) {
  if (!LANGS[lang]) lang = DEFAULT_LANG;
  const res = await fetch(LANGS[lang].file);
  if (!res.ok) throw new Error('failed to load ' + LANGS[lang].file);
  DATA = await res.json();
  state.lang = lang;
  state.category = '';
  state.tags.clear();
  state.shown = PAGE_SIZE;
  try { localStorage.setItem('costume-lang', lang); } catch (e) { /* private mode */ }
  document.querySelectorAll('#langSwitch button').forEach(b => b.setAttribute('aria-pressed', String(b.getAttribute('data-lang') === lang)));
  applyStrings();
  renderAll();
}

(async () => {
  let saved = DEFAULT_LANG;
  try { saved = localStorage.getItem('costume-lang') || DEFAULT_LANG; } catch (e) { /* private mode */ }
  applyStrings();
  await loadLang(LANGS[saved] ? saved : DEFAULT_LANG);
})();
})();
</script>
</body>
</html>
'''

BUILD_SH = '''#!/usr/bin/env bash
# Build the Cloudflare Pages publish directory dist/.
# Only copies files the site actually serves. Image directories are
# copied only when present; image paths themselves always come from
# the generated data files, never from this script.
set -euo pipefail

cd "$(dirname "$0")"

DST="${DST:-dist}"
rm -rf "$DST"
mkdir -p "$DST"

cp index.html _headers "$DST/"
[ -f robots.txt ] && cp robots.txt "$DST/"
[ -f sitemap.xml ] && cp sitemap.xml "$DST/"
[ -f og-cover.jpg ] && cp og-cover.jpg "$DST/"
for d in data thumbs img orig; do
  [ -d "$d" ] && cp -R "$d" "$DST/"
done

echo "dist ready: $DST"
du -sh "$DST"
find "$DST" -type f | wc -l
'''

HEADERS_TXT = '''# Images: immutable, one year
/img/*
  Cache-Control: public, max-age=31536000, immutable
/thumbs/*
  Cache-Control: public, max-age=31536000, immutable
/orig/*
  Cache-Control: public, max-age=31536000, immutable

# Data files: one day
/data/*
  Cache-Control: public, max-age=86400

# HTML: revalidate every time
/index.html
  Cache-Control: public, max-age=0, must-revalidate
/
  Cache-Control: public, max-age=0, must-revalidate

# SEO files
/robots.txt
  Cache-Control: public, max-age=3600
'''

ROBOTS_TXT = '''User-agent: *
Allow: /
# TODO: add a Sitemap line after the production domain is decided.
'''


def build_html(ui, cats, default_lang, repo_url):
    html = HTML_TEMPLATE
    display = {}
    for c in cats:
        token = c["label"].get("en") or c["key"]
        sid = "cat_" + str(token)
        display[c["key"]] = {lang: (ui.get(lang, {}).get(sid) or c["label"].get(lang) or c["key"]) for lang in LANGS}
    html = html.replace("__UI_JSON__", json.dumps(ui, ensure_ascii=False))
    html = html.replace("__JA_SYN_JSON__", json.dumps(JA_SEARCH_SYNONYMS, ensure_ascii=False))
    html = html.replace("__CATS_JSON__", json.dumps(cats, ensure_ascii=False))
    html = html.replace("__CAT_DISPLAY_JSON__", json.dumps(display, ensure_ascii=False))
    html = html.replace("__DEFAULT_LANG__", default_lang)
    html = html.replace("__REPO_URL__", repo_url)
    html = html.replace("__SOURCE_URL__", SOURCE_URL)
    html = html.replace("__CREATOR_URL__", CREATOR_URL)
    return html


def write_outputs(out_dir, per_lang, ui, cats, default_lang, repo_url, verify_src):
    data_dir = os.path.join(out_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    for lang in LANGS:
        path = os.path.join(out_dir, DATA_NAMES[lang])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(per_lang[lang], f, ensure_ascii=False, indent=1)
            f.write("\n")
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_html(ui, cats, default_lang, repo_url))
    with open(os.path.join(out_dir, "build.sh"), "w", encoding="utf-8") as f:
        f.write(BUILD_SH)
    os.chmod(os.path.join(out_dir, "build.sh"), 0o755)
    with open(os.path.join(out_dir, "_headers"), "w", encoding="utf-8") as f:
        f.write(HEADERS_TXT)
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(ROBOTS_TXT)
    with open(os.path.join(out_dir, "verify_costume.py"), "w", encoding="utf-8") as f:
        f.write(verify_src)
    os.chmod(os.path.join(out_dir, "verify_costume.py"), 0o755)

VERIFY_SRC = r'''#!/usr/bin/env python3
# Verify a generated costume gallery site directory.
# Usage:
#   verify_costume.py --site-dir DIR [--images-root DIR] [--dict CSV]
#       [--dict-map JSON] [--ui CSV] [--expect-count N] [--strict-images]
# Checks: the four data files parse, share ids in the same order and have
# no duplicates; every item has id/thumb/image/orig; image files exist
# under --images-root (warning unless --strict-images); dictionary and
# UI coverage when those inputs are given; index.html references all
# four data files and defaults to English.
# Exit: 0 ok (warnings allowed), 1 structural errors, 2 strict image errors.
import argparse
import csv
import json
import os
import sys

LANGS = ["ja", "en", "zh-CN", "zh-TW"]
DATA_NAMES = {lang: "data/costume-%s.json" % lang for lang in LANGS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-dir", default=".")
    ap.add_argument("--images-root", default=None)
    ap.add_argument("--dict", default=None)
    ap.add_argument("--dict-map", default=None)
    ap.add_argument("--djson", default=None)
    ap.add_argument("--ui", default=None)
    ap.add_argument("--expect-count", type=int, default=None)
    ap.add_argument("--strict-images", action="store_true")
    args = ap.parse_args()
    errors, warnings = [], []
    images_root = args.images_root or args.site_dir

    datasets = {}
    for lang in LANGS:
        path = os.path.join(args.site_dir, DATA_NAMES[lang])
        if not os.path.exists(path):
            errors.append("missing data file: %s" % DATA_NAMES[lang])
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (ValueError, OSError) as e:
            errors.append("%s: invalid JSON: %s" % (DATA_NAMES[lang], e))
            continue
        if not isinstance(data, list):
            errors.append("%s: top level is not an array" % DATA_NAMES[lang])
            continue
        datasets[lang] = data

    if datasets:
        base = datasets.get("ja") or next(iter(datasets.values()))
        base_ids = [str(it.get("id", "")) for it in base]
        if len(base_ids) != len(set(base_ids)):
            errors.append("duplicate ids in base data file")
        if args.expect_count is not None and len(base) != args.expect_count:
            errors.append("count %d != expected %d" % (len(base), args.expect_count))
        for lang, data in datasets.items():
            ids = [str(it.get("id", "")) for it in data]
            if ids != base_ids:
                errors.append("%s: id list/order differs from base file" % DATA_NAMES[lang])
            for i, it in enumerate(data):
                for field in ("id", "category", "keywords", "thumb", "image", "orig", "search"):
                    if field not in it:
                        errors.append("%s item %d (%s): missing field %s" % (DATA_NAMES[lang], i, it.get("id"), field))
                if not str(it.get("id", "")).strip():
                    errors.append("%s item %d: empty id" % (DATA_NAMES[lang], i))
                for field in ("thumb", "image", "orig"):
                    if not str(it.get(field, "")).strip():
                        errors.append("%s item %d (%s): empty %s" % (DATA_NAMES[lang], i, it.get("id"), field))
                if not isinstance(it.get("keywords"), list):
                    errors.append("%s item %d (%s): keywords is not a list" % (DATA_NAMES[lang], i, it.get("id")))
                if not str(it.get("category", "")).strip():
                    warnings.append("%s item %d (%s): empty category" % (DATA_NAMES[lang], i, it.get("id")))
                if isinstance(it.get("keywords"), list) and not it["keywords"]:
                    warnings.append("%s item %d (%s): no keywords" % (DATA_NAMES[lang], i, it.get("id")))

        missing_images = []
        checked = 0
        for it in base:
            for field in ("thumb", "image", "orig"):
                p = str(it.get(field, ""))
                if not p or p.startswith(("http://", "https://", "data:")):
                    continue
                checked += 1
                if not os.path.exists(os.path.join(images_root, p)):
                    missing_images.append(p)
        if missing_images:
            msg = "missing image files: %d of %d checked (showing %d): %s" % (
                len(missing_images), checked, min(20, len(missing_images)), ", ".join(missing_images[:20]))
            if args.strict_images:
                errors.append(msg)
            else:
                warnings.append(msg)
        print("items: %d, image paths checked: %d, missing: %d" % (len(base), checked, len(missing_images)))

    if args.dict and args.dict_map:
        with open(args.dict_map, encoding="utf-8-sig") as f:
            mapping = json.load(f)
        with open(args.dict, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        keys = set()
        for row in rows:
            k = (row.get(mapping["key"]) or "").strip()
            if k:
                keys.add(k)
        if args.djson:
            with open(args.djson, encoding="utf-8-sig") as f:
                text = f.read().strip()
            if text.startswith("const"):
                text = text[text.find("=") + 1:].strip()
            if text.endswith(";"):
                text = text[:-1].strip()
            raw = json.loads(text)
            if isinstance(raw, dict):
                for kk in ("items", "data", "costumes", "D", "list"):
                    if isinstance(raw.get(kk), list):
                        raw = raw[kk]
                        break
            cats = set(str(it.get("カテゴリ", "")).strip() for it in raw if isinstance(it, dict))
            toks = set()
            for it in raw:
                if not isinstance(it, dict):
                    continue
                kw = it.get("キーワード", "")
                if isinstance(kw, list):
                    toks.update(str(t).strip() for t in kw)
                else:
                    toks.update(t for t in str(kw).replace(",", " ").split() if t)
            for kind, values in (("category", cats), ("keyword", toks)):
                hit = values & keys
                cov = (100.0 * len(hit) / len(values)) if values else 100.0
                print("dict coverage %s: %d/%d (%.1f%%)" % (kind, len(hit), len(values), cov))
                if not values:
                    continue
                if len(hit) == 0:
                    errors.append("dict coverage %s is 0%%: dictionary keys do not match any source values; check --dict-map / key semantics" % kind)
                elif len(hit) < len(values):
                    warnings.append("untranslated %s terms: %s" % (kind, ", ".join(sorted(values - keys)[:20])))
        else:
            print("dict coverage skipped: no --djson given (coverage must be measured against source terms)")
        print("dict rows: %d, distinct keys: %d" % (len(rows), len(keys)))

    if args.ui:
        with open(args.ui, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            rows = list(reader)
        def find_col(cands):
            for c in cands:
                if c in headers:
                    return c
            return None
        cols = {
            "ja": find_col(["ja", "ui_ja", "japanese", "jp"]),
            "en": find_col(["en", "ui_en", "english"]),
            "zh-CN": find_col(["zh-CN", "zh_CN", "ui_zh-CN", "ui_zh_CN", "sc", "simplified"]),
            "zh-TW": find_col(["zh-TW", "zh_TW", "ui_zh-TW", "ui_zh_TW", "tc", "traditional"]),
        }
        for lang in LANGS:
            col = cols[lang]
            missing = sum(1 for r in rows if not (r.get(col) or "").strip()) if col else len(rows)
            print("ui coverage %s: %d/%d present" % (lang, len(rows) - missing, len(rows)))
            if lang == "en" and missing:
                errors.append("ui: %d English strings empty; the default language must be complete" % missing)
            elif missing:
                warnings.append("ui: %d %s strings empty (fallback will be used)" % (missing, lang))

    html_path = os.path.join(args.site_dir, "index.html")
    if not os.path.exists(html_path):
        errors.append("missing index.html")
    else:
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        for lang in LANGS:
            if ("data/costume-%s.json" % lang) not in html:
                errors.append("index.html does not reference data/costume-%s.json" % lang)
        if 'DEFAULT_LANG' not in html or '"en"' not in html and "'en'" not in html:
            warnings.append("index.html default language marker not found")
        if "ギア" not in html:
            warnings.append("index.html footer attribution does not mention the original author")
        if "non-commercial" not in html.lower():
            warnings.append("index.html footer does not mention non-commercial use")
    for name in ("build.sh", "_headers"):
        if not os.path.exists(os.path.join(args.site_dir, name)):
            errors.append("missing %s" % name)

    print("errors: %d, warnings: %d" % (len(errors), len(warnings)))
    for e in errors:
        print("ERROR: " + e)
    for w in warnings[:30]:
        print("WARN: " + w)
    if errors:
        print("VERIFY FAILED")
        return 1
    if warnings:
        print("VERIFY OK WITH WARNINGS")
        return 0
    print("VERIFY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def build_cats(items, lookup):
    cats = []
    seen = set()
    for raw in items:
        cat = str(raw.get(F_CAT) or "").strip()
        if not cat or cat in seen:
            continue
        seen.add(cat)
        label = {}
        for lang in LANGS:
            t = translate(lookup, cat, lang, "category", set())
            label[lang] = t if t else cat
        cats.append({"key": cat, "label": label})
    return cats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate the multilingual costume gallery site.")
    ap.add_argument("--djson", required=True)
    ap.add_argument("--dict", required=True)
    ap.add_argument("--dict-map", required=True)
    ap.add_argument("--ui", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--default-lang", default="en", choices=LANGS)
    ap.add_argument("--repo-url", default="https://github.com/dheimanb/ai-costume-gallery-i18n")
    args = ap.parse_args(argv)

    warnings = []
    try:
        items = load_djson(args.djson)
        lookup = load_dict(args.dict, args.dict_map, warnings)
        strings = load_ui(args.ui)
        ui, fallbacks = resolve_ui(strings)
        per_lang, untranslated, unused = build_data(items, lookup, warnings)
        cats = build_cats(items, lookup)
    except GenError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    write_outputs(args.out, per_lang, ui, cats, args.default_lang, args.repo_url, VERIFY_SRC)

    print(f"items: {len(items)}")
    print(f"categories: {len(cats)}")
    print(f"dictionary rows: {len(lookup)}, unused keys: {len(unused)}")
    if unused:
        print(f"unused dictionary keys (first 10): {sorted(unused)[:10]}")
    print(f"untranslated terms: {len(untranslated)} (term, kind, language)")
    for term, kind, lang in sorted(untranslated)[:20]:
        print(f"  UNTRANSLATED {kind} {lang}: {term}")
    print(f"UI fallback strings: {len(fallbacks)}")
    for sid, lang, src in fallbacks[:20]:
        print(f"  UI FALLBACK {sid} {lang} <- {src}")
    for w in warnings[:20]:
        print(f"WARN: {w}")
    print(f"output: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
