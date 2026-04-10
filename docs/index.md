# LLMWiki

LLMWiki treats knowledge like a maintained codebase instead of a one-shot retrieval index.

## Core Ideas
1. Compilation over retrieval: sources become persistent Markdown pages.
2. Local-first memory: raw sources, compiled pages, and metadata live in your vault.
3. Compounding maintenance: reflection, evolution, and audits improve the wiki over time.
4. Shared output surface: the same vault feeds CLI workflows, dashboard APIs, and Quartz.

## Runtime Surface
- Ingest: `ingest`, `sync`, `watch`
- Knowledge ops: `ask`, `reflect`, `evolve`, `maintain`, `brew`, `chat`, `map`
- Services: `dashboard` (FastAPI), `server` (Quartz), `maintenance`, `gateway`, `up`
- Build: `build`

Provider modes:
- `openai`: extractor-driven local parsing before gardening.
- `gemini-cli` / `codex-cli`: local file extraction is skipped and providers handle files directly.

See `docs/cli.md` for command details.
