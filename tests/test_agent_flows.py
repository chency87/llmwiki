import pytest
import asyncio
from pydantic_ai.models.test import TestModel
from llmwiki.gardener import Gardener, QAEngine
from llmwiki.gardener.dispatcher import Dispatcher

@pytest.fixture
def test_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "raw").mkdir()
    (vault / "pages").mkdir()
    (vault / "pages" / "entities").mkdir()
    (vault / "pages" / "summaries").mkdir()
    (vault / "pages" / "models").mkdir()
    (vault / "pages" / "qa").mkdir()
    return str(vault)

def test_cli_import():
    from llmwiki.cli import cli
    assert cli is not None

def test_gardener_mock(test_vault):
    mock_model = TestModel()
    gardener = Gardener(model=mock_model, vault_path=test_vault)
    asyncio.run(gardener.process_new_source("test.txt", "Some text about Python."))
    # pydantic-ai TestModel doesn't actually call tools by default 
    # unless configured, but we verify it runs without crashing.
    assert True

def test_qa_mock(test_vault):
    mock_model = TestModel()
    qa = QAEngine(model=mock_model, vault_path=test_vault)
    asyncio.run(qa.ask("What is Python?"))
    assert True

def test_dispatcher_mock(test_vault):
    mock_model = TestModel()
    dispatcher = Dispatcher(model=mock_model, vault_path=test_vault)
    asyncio.run(dispatcher.dispatch("Help me organize my notes."))
    assert True
