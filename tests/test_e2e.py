import pytest
import asyncio
import os
from pathlib import Path
from pydantic_ai.models.test import TestModel
from llmwiki.ingest import Processor
from llmwiki.gardener import Gardener, QAEngine

@pytest.fixture
def e2e_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "raw").mkdir()
    (vault / "pages").mkdir()
    (vault / "pages" / "entities").mkdir()
    (vault / "pages" / "summaries").mkdir()
    (vault / "pages" / "models").mkdir()
    (vault / "pages" / "qa").mkdir()
    # Create an initial _index.md
    (vault / "pages" / "_index.md").write_text("# Wiki Index")
    return str(vault)

def test_end_to_end_flow(e2e_vault):
    # 1. Ingest a document
    source_file = Path(e2e_vault) / "python_intro.txt"
    source_file.write_text("Python is a high-level programming language.")
    
    processor = Processor(vault_path=e2e_vault)
    dest, text, needs_processing = processor.process_file(str(source_file))
    assert needs_processing is True
    assert "Python" in text
    
    # 2. Gardening (Mocked LLM)
    mock_model = TestModel()
    gardener = Gardener(model=mock_model, vault_path=e2e_vault)
    asyncio.run(gardener.process_new_source(os.path.basename(dest), text))
    processor.mark_as_done(dest)
    
    # 3. QA (Mocked LLM)
    qa = QAEngine(model=mock_model, vault_path=e2e_vault)
    answer = asyncio.run(qa.ask("What is Python?"))
    
    assert os.path.exists(os.path.join(e2e_vault, "pages/qa/what-is-python.md"))
    # pydantic-ai TestModel might return tool calls or default success string
    assert len(answer) > 0
    
    # Verify manifest
    assert processor.manifest.is_processed(os.path.basename(dest), processor.manifest.get_file_hash(dest)) is True
