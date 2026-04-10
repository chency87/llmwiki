# Agent Workflows

This page maps user-facing workflows to the current runtime behavior.

## Ingest Path (`ingest`, `sync`, `watch`)

```mermaid
sequenceDiagram
    participant U as User/Watcher
    participant P as Processor
    participant M as Manifest/Store
    participant G as Gardener

    U->>P: New file path or URL
    P->>M: try_acquire_lock(filename, hash)
    alt lock denied
        M-->>P: already PROCESSING/PROCESSED (same hash)
        P-->>U: skip
    else lock acquired
        P->>P: copy/sanitize into vault/raw
        P->>P: extract text (skipped for *-cli local files)
        P->>G: process_new_source(...)
        G-->>P: success/failure
        P->>M: mark PROCESSED or ERROR
    end
```

## QA Path (`ask`)

```mermaid
sequenceDiagram
    participant U as User
    participant Q as QAEngine
    participant T as VaultTools/Store
    participant V as Vault

    U->>Q: ask(question)
    Q->>T: read _index + top related entities
    Q->>Q: run agent with initial context
    Q->>V: write pages/qa/<slug>.md
    Q-->>U: return answer
```

## Maintenance and Services

- `maintenance` runs `reflect` -> `evolve` -> `maintain` in a loop with `runtime.maintenance_interval_s` (or `--interval`).
- `dashboard` and `server` update heartbeats; `watch` and `maintenance` also emit heartbeats.
- `up` starts process orchestration only; it does not run `quartz build` automatically.
- `gateway` is optional and only starts when `[gateway].enabled = true`.
