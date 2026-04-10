from click.testing import CliRunner

import llmwiki.cli as cli_module
from llmwiki.db.store import Store
from llmwiki.utils.config import Settings
from llmwiki.utils.vault_bootstrap import ensure_vault_initialized


def test_ensure_vault_initialized_creates_empty_template(tmp_path):
    vault = tmp_path / "vault"

    changed = ensure_vault_initialized(str(vault))

    assert changed is True
    assert (vault / "raw").is_dir()
    assert (vault / "pages").is_dir()
    assert (vault / "pages" / "entities").is_dir()
    assert (vault / "pages" / "summaries").is_dir()
    assert (vault / "pages" / "models").is_dir()
    assert (vault / "pages" / "qa").is_dir()
    assert (vault / "artifacts").is_dir()
    assert (vault / "raw" / ".gitkeep").exists()
    assert (vault / "pages" / "_index.md").exists()
    assert (vault / "pages" / "schema.md").exists()
    assert (vault / ".llmwiki" / "llmwiki.db").exists()
    schema = (vault / "pages" / "schema.md").read_text(encoding="utf-8")
    assert "## Page Types" in schema
    assert "## Ingest Workflow" in schema
    assert "## Question Answering Workflow" in schema
    assert "## Maintenance Workflow" in schema


def test_ensure_vault_initialized_is_idempotent_and_preserves_existing_files(tmp_path):
    vault = tmp_path / "vault"
    ensure_vault_initialized(str(vault))

    index_path = vault / "pages" / "_index.md"
    custom_index = "# Custom Index\n"
    index_path.write_text(custom_index, encoding="utf-8")

    changed = ensure_vault_initialized(str(vault))

    assert changed is False
    assert index_path.read_text(encoding="utf-8") == custom_index


def test_ensure_vault_initialized_repairs_partial_vault_without_overwriting(tmp_path):
    vault = tmp_path / "vault"
    (vault / "pages").mkdir(parents=True)
    (vault / "pages" / "_index.md").write_text("# Existing Index\n", encoding="utf-8")

    changed = ensure_vault_initialized(str(vault))

    assert changed is True
    assert (vault / "pages" / "_index.md").read_text(encoding="utf-8") == "# Existing Index\n"
    assert (vault / "pages" / "schema.md").exists()
    assert (vault / "raw").is_dir()
    assert (vault / ".llmwiki" / "llmwiki.db").exists()


def test_cli_bootstraps_vault_before_command_execution(tmp_path, monkeypatch):
    calls = []
    vault = tmp_path / "vault"

    monkeypatch.setattr(cli_module, "check_dependency", lambda name: True)
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda cmd, cwd, check: calls.append((cmd, cwd, check)),
    )

    config = Settings()
    config.paths.vault = str(vault)

    result = CliRunner().invoke(cli_module.cli, ["build"], obj=config)

    assert result.exit_code == 0, result.output
    assert (vault / "pages" / "_index.md").exists()
    assert (vault / "pages" / "schema.md").exists()
    assert Store(str(vault)).get_manifest_stats() == {}
    assert calls == [(["npx", "quartz", "build"], "quartz", True)]
