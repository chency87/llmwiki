# LLMWiki Architecture

LLMWiki is a local-first pipeline that compiles sources into persistent Markdown and keeps runtime state in SQLite.

## Runtime Components

```mermaid
graph TD
    User([User]) --> CLI[CLI commands]
    User --> Gateway[Gateway channels]

    CLI --> Processor[Ingest Processor]
    Processor --> VaultRaw[vault/raw]
    Processor --> Store[(SQLite Store)]

    CLI --> Agents[Gardener / QA / Reflector / Evolver / Maintainer / Writer]
    Gateway --> Dispatcher[Dispatcher (planner-first)]
    Dispatcher --> Planner[Planner agent]

    Agents --> Tools[Vault tools + SQLite entity search + query_data_file]
    Tools --> VaultPages[vault/pages + vault/artifacts]
    Tools --> Store

    CLI --> Dashboard[FastAPI dashboard]
    Dashboard --> Store
```

## Data and State Boundaries

- Vault files:
- `vault/raw/` stores local files and URL extracts.
- `vault/pages/` stores generated wiki pages and QA output.
- `vault/artifacts/` stores long-form outputs from `brew`.
- Runtime DB (`vault/.llmwiki/llmwiki.db`):
- `manifest`, `entities`, `entities_fts`, `links`, `sessions`, `heartbeat`, `logs`.
- Analytical SQL:
- `query_data_file` uses DuckDB in-memory per tool call for large structured files in `vault/raw/`.

## Capability Surface

- Native tools are registered through `CapabilitiesManager` and attached to agents.
- Entity/backlink/knowledge-map reads are backed directly by `Store` (SQLite) via shared agent deps.
- MCP settings exist in config (`[mcp.servers]`), but MCP client initialization is currently scaffolded (not active runtime integration).

## Service Layer

- `dashboard`: FastAPI UI and APIs (`/`, `/api/stats`, `/api/logs`, `/api/knowledge`).
- `server`: Quartz preview (`npx quartz build --serve`).
- `gateway`: optional Telegram/REST channel manager.
- `up`: launches `watch`, `dashboard`, `maintenance`, `server`, and optional `gateway`.
- `chat`/gateway dispatch currently returns planner output from `Dispatcher.dispatch()`.
