import pytest
from llmwiki.gardener.tools.vault_tools import VaultTools

@pytest.fixture
def vt(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return VaultTools(vault_path=str(vault))

def test_vault_tools_write_read(vt):
    res = vt.write_page("test", "hello")
    assert "Successfully" in res
    content = vt.read_page("test")
    assert content == "hello"

def test_vault_tools_log(vt):
    vt.append_log("Action performed")
    log_content = vt.read_page("log")
    assert "Action performed" in log_content
