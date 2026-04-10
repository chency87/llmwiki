from pathlib import Path

import llmwiki.cli as cli_module
from click.testing import CliRunner
from llmwiki.utils.config import Settings


def test_sync_to_quartz_removes_deleted_pages(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    vault = tmp_path / "vault"
    pages = vault / "pages"
    pages.mkdir(parents=True)
    (pages / "kept.md").write_text("fresh", encoding="utf-8")

    quartz_content = tmp_path / "quartz" / "content"
    quartz_content.mkdir(parents=True)
    (quartz_content / "stale.md").write_text("old", encoding="utf-8")

    cli_module.sync_to_quartz(str(vault))

    assert not (quartz_content / "stale.md").exists()
    assert (quartz_content / "kept.md").read_text(encoding="utf-8") == "fresh"


def test_build_syncs_before_running_quartz(monkeypatch):
    calls = []

    monkeypatch.setattr(cli_module, "check_dependency", lambda name: True)
    monkeypatch.setattr(cli_module, "sync_to_quartz", lambda vault_path: calls.append(("sync", vault_path)))
    monkeypatch.setattr(
        cli_module.subprocess,
        "run",
        lambda cmd, cwd, check: calls.append(("run", cmd, cwd, check)),
    )
    config = Settings()
    config.paths.vault = "/tmp/test-vault"

    result = CliRunner().invoke(cli_module.cli, ["build"], obj=config)

    assert result.exit_code == 0, result.output
    assert calls == [
        ("sync", "/tmp/test-vault"),
        ("run", ["npx", "quartz", "build"], "quartz", True),
    ]


def test_server_forwards_host_and_port_to_quartz(monkeypatch):
    calls = []

    class DummyStore:
        def __init__(self, vault_path):
            self.vault_path = vault_path

        def set_heartbeat(self, name):
            calls.append(("heartbeat", name))

    class DummyThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            calls.append(("thread-started", self.daemon))

    monkeypatch.setattr(cli_module, "check_dependency", lambda name: True)
    monkeypatch.setattr(cli_module.subprocess, "run", lambda cmd, cwd, check: calls.append(("run", cmd, cwd, check)))
    monkeypatch.setattr("llmwiki.db.store.Store", DummyStore)
    monkeypatch.setattr("threading.Thread", DummyThread)

    config = Settings()
    config.paths.vault = "/tmp/test-vault"

    result = CliRunner().invoke(
        cli_module.cli,
        ["server", "--port", "4321", "--host", "0.0.0.0"],
        obj=config,
    )

    assert result.exit_code == 0, result.output
    assert ("thread-started", True) in calls
    assert (
        "run",
        ["npx", "quartz", "build", "--serve", "--port", "4321", "--host", "0.0.0.0"],
        "quartz",
        True,
    ) in calls
