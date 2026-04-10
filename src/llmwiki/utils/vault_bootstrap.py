from pathlib import Path

from llmwiki.db.store import Store


INDEX_TEMPLATE = """# Wiki Index

This vault is empty.

Start here:
- Add a source with `llmwiki ingest <path-or-url>`
- Process pending sources with `llmwiki sync`
- Ask a question with `llmwiki ask "your question"`
- Generate the relationship graph with `llmwiki map`
"""

SCHEMA_TEMPLATE = """# Wiki Schema

This file is the operating contract for the wiki maintainer agents.

The goal is to keep the vault as a disciplined, evolving knowledge base rather than a loose chat transcript.
Treat this file as editable configuration: update it as the domain, page patterns, and workflows become clearer.

## Mission
- Convert sources into durable Markdown knowledge.
- Prefer maintaining a small number of strong canonical pages over creating many overlapping pages.
- Keep the wiki navigable by structure, links, and naming consistency.

## Page Types
- `entities/`: canonical pages for people, organizations, projects, concepts, methods, datasets, systems, and topics.
- `summaries/`: source-oriented summaries created from individual ingested files or URLs.
- `models/`: higher-level mental models, frameworks, and abstractions extracted from multiple pages.
- `qa/`: saved answers to concrete user questions.
- `_index.md`: the root orientation page for the vault.

## Naming Conventions
- Use clear human-readable page titles.
- Prefer one canonical page per concept.
- Reuse and update existing pages when they already represent the concept.
- Create a new page only when the concept is genuinely distinct.
- File names should match the page title unless a subfolder structure is required.

## Linking Conventions
- Use `[[Wiki Links]]` for internal references.
- Add links between related pages in both directions when the relationship matters.
- Prefer linking to canonical entity pages instead of repeating explanations.
- When a page mentions an important concept repeatedly, that concept should usually have its own page.

## Page Structure
- Start pages with a clear title.
- Keep explanations concise, specific, and grounded in the source material.
- Prefer sections and bullets when they improve navigation.
- Preserve useful source context, but avoid turning the wiki into raw note dumps.
- When saving answers in `qa/`, make the answer readable on its own and link back to supporting pages.

## Classification
- When writing or updating pages, apply categories and tags consistently if the workflow supports them.
- Prefer a small, stable vocabulary over many near-duplicate labels.
- Reuse existing categories and tags when possible.

## Ingest Workflow
- Read the new source and identify its main entities, claims, methods, datasets, or themes.
- Check the existing wiki before creating new pages.
- Update all relevant canonical pages, not just one summary page.
- Create or update a `summaries/` page for source-specific context when useful.
- Preserve important terminology, names, and relationships from the source.
- If the source conflicts with existing pages, update the wiki carefully and preserve uncertainty explicitly.

## Question Answering Workflow
- Start from `_index.md`, `schema.md`, and the most relevant existing pages.
- Answer from the wiki when the information is already present.
- Use raw sources only when the wiki context is insufficient.
- Save durable answers under `qa/` using a slug based on the question.
- Link the saved answer to the canonical pages it depends on.
- If the question reveals a missing canonical page, create or improve that page as part of the answering process when appropriate.

## Maintenance Workflow
- Merge redundant pages when they represent the same concept.
- Strengthen weak internal linking when related pages are isolated.
- Improve clarity, naming, and structure when pages become noisy or repetitive.
- Preserve canonical pages and reduce duplication.
- Add or refine `models/` pages when multiple pages support a reusable abstraction.

## Quality Bar
- Be accurate, concrete, and specific.
- Prefer synthesis over paraphrased repetition.
- Prefer updating existing knowledge over scattering similar facts across many pages.
- Keep the wiki useful for future readers who were not part of the original conversation.
"""


def ensure_vault_initialized(vault_path: str) -> bool:
    vault_root = Path(vault_path).resolve()

    directories = [
        vault_root / "raw",
        vault_root / "pages",
        vault_root / "pages" / "entities",
        vault_root / "pages" / "summaries",
        vault_root / "pages" / "models",
        vault_root / "pages" / "qa",
        vault_root / "artifacts",
    ]

    changed = False
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            changed = True

    placeholder_dirs = [
        vault_root / "raw",
        vault_root / "pages" / "entities",
        vault_root / "pages" / "summaries",
        vault_root / "pages" / "models",
        vault_root / "pages" / "qa",
        vault_root / "artifacts",
    ]

    for directory in placeholder_dirs:
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
            changed = True

    templates = {
        vault_root / "pages" / "_index.md": INDEX_TEMPLATE,
        vault_root / "pages" / "schema.md": SCHEMA_TEMPLATE,
    }

    for path, content in templates.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            changed = True

    db_path = vault_root / ".llmwiki" / "llmwiki.db"
    db_existed = db_path.exists()
    Store(str(vault_root))
    if not db_existed and db_path.exists():
        changed = True

    return changed
