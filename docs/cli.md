# CLI Reference

## Root Options
- `--config <path>`: load a specific `llmwiki.toml`.
- `--vault <path>`: override vault directory.

## Ingestion Commands

### `llmwiki ingest <source>`
Ingest a local file path or URL and trigger gardening.
If the source is already in `PROCESSING` or already `PROCESSED` for the same hash, ingestion is skipped.

Provider behavior:
- `openai`: extract text locally, then pass text to the agent.
- `gemini-cli` / `codex-cli`: skip local extraction for local files and pass file paths for native CLI processing.
- URLs are extracted to local text first in all modes.

Options:
- `--provider <name>` (`openai`, `gemini-cli`, `codex-cli`)
- `--model <name>` (for OpenAI-compatible backends; default `gpt-4o`)
- `--base-url <url>`
- `--api-key <key>`

### `llmwiki sync`
Scan `vault/raw/` and process eligible files in parallel (skips unchanged processed files and in-flight files).

Options:
- `--provider <name>`
- `--model <name>`
- `--concurrency <int>`
- `--base-url <url>`
- `--api-key <key>`

### `llmwiki watch`
Watch `vault/raw/` for added/modified files and process automatically.

Options:
- `--provider <name>`
- `--model <name>`
- `--base-url <url>`
- `--api-key <key>`

## Knowledge Commands

### `llmwiki reflect`
Run a reflection pass to generate higher-level model pages.

### `llmwiki ask <question>`
Answer a question from vault knowledge and save the result under `vault/pages/qa/`.

### `llmwiki evolve`
Run structural evolution (merge redundant entities, strengthen links).

### `llmwiki maintain`
Run a quality audit (detect contradictions, broken links, stale information).

### `llmwiki brew <topic>`
Generate a long-form artifact under `vault/artifacts/`.

### `llmwiki chat <message>`
Send a request to the dispatcher workflow.

### `llmwiki map`
Generate a weighted Mermaid knowledge graph page at `vault/pages/graph.md` from the `links` table.

Shared options for `reflect`, `ask`, `evolve`, `maintain`, `brew`, `chat`:
- `--provider <name>`
- `--model <name>`
- `--base-url <url>`
- `--api-key <key>`

## Service Commands

### `llmwiki dashboard`
Start the FastAPI observability dashboard.

Options:
- `--port <int>`
- `--host <host>`

### `llmwiki maintenance`
Run periodic `reflect` + `evolve` + `maintain` cycles.

Options:
- `--interval <seconds>`

### `llmwiki gateway`
Start the multi-channel gateway manager.

Runtime behavior:
- Returns immediately with a warning if `[gateway].enabled` is `false`.
- Registers Telegram when `[gateway.telegram].token` is set.
- Registers REST when `[gateway.rest].enabled` is `true`.

### `llmwiki server`
Start the Quartz preview server (`npx quartz build --serve`).

Options:
- `--port <int>`
- `--host <host>`

### `llmwiki up`
Start `watch`, `dashboard`, `maintenance`, and `server` together; add `gateway` when enabled in config.
Behavior notes:
- Forwards root `--vault` to child commands.
- Child commands resolve config from normal discovery paths; a custom root `--config` path is not forwarded.

## Build Command

### `llmwiki build`
Run `npx quartz build` in `quartz/`.
