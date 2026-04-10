# Quartz Visualization

LLMWiki uses **Quartz v4** (https://quartz.jzhao.xyz/) for high-fidelity visualization of the knowledge codebase.

## Features
- **Obsidian Native**: Support for `[[Wiki Links]]`, `![[Embeds]]`, and Callouts.
- **Interactive Graph**: A full D3-based knowledge graph available in the UI.
- **Backlinks**: Automatically renders every incoming link at the bottom of the page.
- **Global Search**: High-speed, client-side full-text search.
- **SPA Navigation**: Smooth, instant page transitions without full reloads.

## Usage

### Building the Site
To generate the static HTML into `quartz/public/`:
```bash
llmwiki build
```

### Running the Server
To start the interactive preview server (defaulting to port 1313):
```bash
llmwiki server
```

Quartz v4 in this repository exposes the preview server port through the CLI. The LLMWiki `--host` setting is not forwarded because Quartz does not accept a `--host` flag for `build --serve`.

## Configuration
The visualization layer is configured via:
- `quartz/quartz.config.ts`: Global settings (Title, Base URL, Plugins).
- `quartz/quartz.layout.ts`: Component placement (Sidebar, Graph, Backlinks).

## Content Sync
The AI Crew writes to `vault/pages/`. When building, these files are copied to `quartz/content/` to ensure the visualization matches the current state of the knowledge codebase.
