# task1 — local qwen3:8b first drafts (NOT final)

Harness: `tools/qwen-text-harness` (#18), local Ollama `qwen3:8b`; no cloud model. Scope per bibi on agent-handoff #19.

## Files

| File | What |
|------|------|
| `task1-input.csv` / `task1-output.csv` / `task1-progress.json` | categories: 8 Japanese category terms → en / zh-CN / zh-TW (`ja-trilingual`, prompt 01) |
| `keyword-token-input.csv` | 86 distinct tokens from `キーワード` (split on space), built by script; `token` copied verbatim (case, `polka-dot`); `examples` = up to 3 source strings for context |
| `keyword-token-dict.csv` | **keyword dictionary**: `id,token,examples,zh-CN,zh-TW,flag` (`en-token-zh`, prompt 04); each token translated once |
| `keyword-token-progress.json` | harness resume file |
| `vocab-task1-draft.csv` | all 1407 rows, 11 columns (below) |
| `evidence-*.json` | run summaries |

`vocab-task1-draft.csv` columns: `id, カテゴリ, キーワード, category_en, category_zh-CN, category_zh-TW, category_flag, keyword_en, keyword_zh-CN, keyword_zh-TW, keyword_flag`

- Japanese layer: only `カテゴリ` is Japanese at source. Keywords have no Japanese original; none invented.
- `keyword_en` = source string unchanged.
- `keyword_zh-CN` / `keyword_zh-TW`: mechanical token-by-token mapping through the dictionary, joined with spaces in the source order (no row-by-row model calls). If any token in a row has no translation, both cells stay blank and `keyword_flag = untranslated_tokens:<tokens>`.
- Category columns are not touched by the keyword task. 秋 (244 rows) stays blank with `uncertain_en`.

## Decisions for later (not applied yet)

- Season wording: use 四季 style 春季／夏季／秋季／冬季 in zh-CN and zh-TW (not 春天/夏天). Current category columns still read 春天/夏天/冬季; fix in the final pass together with 秋.

## Review needed

Rows with a non-empty flag need a human. Dictionary rows with flag: `chiffon` (blank, affects 21 rows).
Spot-check of unflagged dictionary entries (qwen was confident, but these look wrong or loose; left unchanged for review):
`briefs` 比基尼 (likely 內褲), `swimsuit` 比基尼 (泳衣/泳裝), `corduroy` 粗花呢 (燈芯絨), `leather` 皮革包 (皮革), `camisole` 罩衫 (吊帶背心), `skirt` 短裙 (裙; clashes with midi/maxi), `midi`/`maxi` 中长裙/长裙 (should be length modifiers), `boots` 短靴 (靴子), `bra` 内衣 (胸罩/文胸), `floral` 花卉 (碎花/印花), `pleated` 褶皱 (百褶), `satin` CN 缎子 vs TW 綢 (緞面), `velvet` CN 天鹅绒 vs TW 絲絨, `choker` 锁骨链 (頸鏈/項圈), `robe` 长袍 (睡袍), `tights`/`stockings` both 丝袜, `heels`/`pumps` both 高跟鞋.
