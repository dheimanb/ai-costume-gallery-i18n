# task1 — ja-trilingual first draft (local qwen3:8b, NOT final)

Harness: `tools/qwen-text-harness` (#18), task `ja-trilingual`, prompt `prompts/01-ja-trilingual.md`, model `qwen3:8b` via local Ollama; no cloud model.

- `task1-input.csv` — harness input built by script from `meta/vocab.csv`: the 8 unique Japanese category terms (`is_en_keyword=false`).
- `task1-output.csv` — harness output (en / zh-CN / zh-TW / flag), 8 rows, validate PASS.
- `task1-progress.json` — harness resume file.
- `vocab-task1-draft.csv` — all 1407 vocab rows: category columns from the qwen glossary; `キーワード` is already an English keyword string on the source site, so per harness rule 1 it is passed through unchanged (`en_keyword_passthrough`), no model call.
- `evidence-ja-trilingual-last-run.json` — run summary.

Why only 8 model rows: vocab.csv has no Japanese keyword field (the site's キーワード is English). Sending 1407 passthrough rows to the model would only reproduce the input. If Chinese translations of the English keyword strings are wanted, that is a separate task (not rule 1) and needs bibi's call.

Rows with a non-empty `flag` need human review.
