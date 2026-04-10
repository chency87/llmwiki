# Memory & Tracking

LLMWiki combines filesystem memory (vault content) with SQLite runtime state.

## 1. Vault Files (Primary Memory)
- `vault/raw/`: source corpus (files and URL extracts)
- `vault/pages/`: compiled pages, QA outputs, model pages, maintenance artifacts
- `vault/artifacts/`: generated long-form outputs (`brew`)

## 2. SQLite Metadata (`vault/.llmwiki/llmwiki.db`)

### `manifest`
Tracks per-source hash and processing state.
State machine in runtime code: `PENDING` -> `PROCESSING` -> `PROCESSED` or `ERROR`.
Ingestion acquires processing locks to avoid duplicate work for unchanged or in-flight files.

### `entities` + `entities_fts`
Knowledge map (`name`, `path`, `summary`) plus optional FTS5 keyword search index.

### `links`
Source-to-target page links used for relationship/backlink workflows.

### `sessions`
Persisted CLI-provider session keys for adapter agents (for example `gemini-cli`, `codex-cli`).

### `heartbeat`
Per-service liveness records for `watch`, `dashboard`, `maintenance`, `server`.

### `logs`
Structured runtime events (`timestamp`, `trace_id`, `task_type`, `category`, `level`, `message`) consumed by dashboard APIs.

## 3. File Log Mirror
- `vault/.llmwiki/system.log` stores local log output for inspection.
