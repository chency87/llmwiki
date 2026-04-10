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
llmwiki server --host 0.0.0.0 --port 1313
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
      - ./llmwiki.toml:/app/llmwiki.toml:ro
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    command: ["llmwiki", "up"]
    ports:
      - "8501:8501"
      - "1313:1313"
      - "8000:8000"
```

## GitHub Actions

The repository includes `.github/workflows/docker.yml` to:
- validate `docker-compose.yml`
- build the Docker image with Buildx

It runs on pull requests, pushes to `main`, and manual dispatch.

## Stopping Services
Use `Ctrl+C` to stop `llmwiki up` and terminate all child services.
