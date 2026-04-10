# Installation Guide

LLMWiki is designed to be a high-performance, local-first knowledge codebase. This guide will walk you through setting up the ecosystem on your local machine or server.

## 📋 Prerequisites

Before installing LLMWiki, ensure you have the following tools installed:

### 1. Core Runtimes
- **Python 3.12+**: The primary logic and agent orchestration layer.
- **Node.js (v20+)**: Required for the Quartz visualization engine.
- **SQLite3**: For the metadata and state machine.

### 2. CLI Agents (Optional but Recommended)
LLMWiki is LLM-agnostic but optimized for:
- **`gemini-cli`**: [Installation Guide](https://github.com/google/gemini-cli)
- **`codex-cli`**: [Installation Guide](https://github.com/google/codex-cli)

---

## 🚀 Step-by-Step Setup

### 1. Clone the Repository
```bash
git clone https://github.com/user/llmwiki.git
cd llmwiki
```

### 2. Install Python Dependencies
We recommend using `uv` for fast, reproducible installs, but standard `pip` works too.
```bash
# Using uv (Recommended)
uv pip install -e .

# Using pip
pip install -e .
```

### 3. Setup the Visualization Layer (Quartz)
Install the dependencies for the Quartz engine:
```bash
cd quartz
npm install
cd ..
```

### 4. Initialize Configuration
Copy the example configuration and customize it for your environment:
```bash
cp llmwiki.toml.example llmwiki.toml
```

---

## ⚙️ Configuration (`llmwiki.toml`)

Edit `llmwiki.toml` to define your vault path and LLM providers.

### Key Sections:
- **`[paths]`**: Define where your Obsidian `vault` is located.
- **`[llm]`**: Set your default provider (`openai`, `gemini-cli`, or `codex-cli`).
- **`[gateway]`**: (Optional) Enable the Telegram or REST API adapters.
- **`[mcp]`**: (Advanced) Configure external Model Context Protocol servers.

---

## 🛠️ Essential Commands

Once configured, you can use the `llmwiki` CLI to manage your knowledge base.

### Starting the Ecosystem
The easiest way to run everything (Watcher, Dashboard, Maintenance, and Web Server) is the `up` command:
```bash
llmwiki up
```

### Ingesting Knowledge
To add a new document or URL to your wiki:
```bash
llmwiki ingest <path-to-file-or-url>
```

### Querying the Vault
Ask a question and save the answer permanently:
```bash
llmwiki ask "What is the core architecture of LingoDB?"
```

### Visualizing the Wiki
Build and serve the Quartz interface:
```bash
# Build the static site
llmwiki build

# Run the preview server (localhost:1313)
llmwiki server
```

---

## 🔍 Verification
After installation, run the following to verify the system integrity:
1. Access the **Observability Dashboard** at `http://localhost:8501`.
2. Access the **Quartz Wiki** at `http://localhost:1313`.
3. Check `vault/.llmwiki/system.log` for any initialization errors.
