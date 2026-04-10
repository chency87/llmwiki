# LLMWiki

LLMWiki is a local-first knowledge wiki: ingest sources, compile them into persistent Markdown pages, and maintain the vault over time.

## What It Does
- Ingest local files and URLs into `vault/raw/`.
- Compile and maintain wiki pages in `vault/pages/`.
- Answer questions and save QA outputs under `vault/pages/qa/`.
- Run maintenance loops (`reflect`, `evolve`, `maintain`) and long-form generation (`brew`).
- Generate a weighted Mermaid knowledge graph page with `map`.
- Serve observability APIs with FastAPI, publish the same vault through Quartz, and optionally expose chat channels through the gateway (`telegram`, `rest`).

## Prerequisites
- Python `3.12+`
- Node.js + npm (for `llmwiki build` and `llmwiki server`)

## Installation
```bash
pip install -e .
cd quartz && npm install
```

## Configuration
Load order:
1. `--config <path>`
2. `./llmwiki.toml`
3. `vault/.llmwiki/llmwiki.toml`
4. Built-in defaults (`src/llmwiki/utils/config.py`)

Example:

```toml
[paths]
vault = "vault"

[llm]
provider = "openai"
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "${OPENAI_API_KEY}"

[executors]
gemini = ["gemini"]
codex = ["codex"]

[ingest]
concurrency = 5
max_parallel_extractors = 4

[dashboard]
host = "0.0.0.0"
port = 8501

[runtime]
maintenance_interval_s = 3600

[server]
host = "0.0.0.0"
port = 1313

[gateway]
enabled = false

[gateway.telegram]
token = ""
allowed_users = []

[gateway.rest]
enabled = false
host = "0.0.0.0"
port = 8000
api_key = ""
```

Provider modes:
- `openai`: local extractors parse files before gardening.
- `gemini-cli` / `codex-cli`: local file extraction is skipped; the provider processes files natively.

## CLI Quick Start
```bash
llmwiki ingest <path-or-url>
llmwiki ask "What are the core concepts?"
llmwiki map
llmwiki maintain
llmwiki up
```

Full command reference: `docs/cli.md`.

## Deployment Modes
- Unified: `llmwiki up` starts `watch`, `dashboard`, `maintenance`, `server`, and `gateway` when `[gateway].enabled = true`.
- Boundary: `up` forwards `--vault` to children, but does not forward a custom root `--config` path.
- Split mode: run each service command independently for custom service flags.

Details: `docs/deployment.md`.

## Containers
Build the image locally:

```bash
docker build -t llmwiki:local .
```

Start the local stack:

```bash
docker compose up --build
```

GitHub Actions also builds the Docker image on push to `main`, on pull requests, and on manual dispatch via `.github/workflows/docker.yml`.
Published image target: `ghcr.io/chency87/llmwiki`
The image and Compose setup use `llmwiki.toml.example` as the checked-in default config, mounted in-container as `/app/llmwiki.toml`.

## Storage Layout
- `vault/raw/`: source files and URL extracts.
- `vault/pages/`: generated and maintained Markdown pages.
- `vault/artifacts/`: outputs from `llmwiki brew`.
- `vault/.llmwiki/llmwiki.db`: SQLite tables for manifest state, entities, links, sessions, heartbeats, and logs.
- `vault/.llmwiki/system.log`: file log output.

For schema details, see `docs/memory.md` and `docs/architecture.md`.
