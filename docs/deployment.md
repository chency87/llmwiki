# Deployment & Orchestration

LLMWiki can run as one orchestrated process (`up`) or as split services.

## Unified Start

```bash
llmwiki up
```

Starts:
1. `llmwiki watch`
2. `llmwiki dashboard`
3. `llmwiki maintenance`
4. `llmwiki server`
5. `llmwiki gateway` (only when `[gateway].enabled = true`)

Boundary behavior:
- Root `--vault` is forwarded to child commands.
- A custom root `--config <path>` is not forwarded.

Use split mode when you need per-service flags.

## Split Mode

### Ingest Watcher
```bash
llmwiki watch
```

### Dashboard (FastAPI)
```bash
llmwiki dashboard --host 0.0.0.0 --port 8501
```

### Maintenance Loop
```bash
llmwiki maintenance --interval 3600
```
Each cycle runs `reflect`, `evolve`, and `maintain`.

### Quartz Server
```bash
llmwiki server --port 1313
```

### Gateway
```bash
llmwiki gateway
```

## Config Defaults

```toml
[paths]
vault = "vault"

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

Quartz note:
- The vendored Quartz preview CLI accepts `--port` but not `--host`. The `[server].host` setting remains as LLMWiki-side metadata and is not forwarded to `npx quartz build --serve`.

## Container Example

```yaml
services:
  llmwiki:
    image: llmwiki:local
    build:
      context: .
      dockerfile: Dockerfile
    init: true
    volumes:
      - ./vault:/app/vault
      - ./llmwiki.toml.example:/app/llmwiki.toml:ro
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    command: ["llmwiki", "up"]
    ports:
      - "8501:8501"
      - "1313:1313"
      - "8000:8000"
```

The checked-in default container config comes from `llmwiki.toml.example`, mounted as `/app/llmwiki.toml` so runtime config discovery still works unchanged.

## GitHub Actions

The repository includes `.github/workflows/docker.yml` to:
- validate `docker-compose.yml`
- build the Docker image with Buildx
- publish `ghcr.io/chency87/llmwiki` on non-PR runs

It runs on pull requests, pushes to `main`, and manual dispatch.

If the GHCR package does not inherit public visibility automatically on first publish, switch it to public once in the GitHub package settings.

## Stopping Services
Use `Ctrl+C` to stop `llmwiki up` and terminate all child services.
