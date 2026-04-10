import pytest
import os
import sqlite3
from llmwiki.db.store import Store

@pytest.fixture
def test_store(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    return Store(vault_path=str(vault_path))

def test_init_db(test_store):
    assert os.path.exists(test_store.db_path)
    with sqlite3.connect(test_store.db_path) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        assert "manifest" in tables
        assert "entities" in tables

def test_manifest_ops(test_store):
    test_store.mark_processed("test.txt", "hash123")
    assert test_store.is_processed("test.txt", "hash123") is True
    assert test_store.is_processed("test.txt", "wrong_hash") is False
    assert test_store.is_processed("other.txt", "hash123") is None

def test_entity_ops(test_store):
    test_store.update_entity("Python", "entities/python.md", "A programming language.")
    kmap = test_store.get_knowledge_map()
    assert "Python" in kmap
    assert kmap["Python"]["summary"] == "A programming language."
    assert kmap["Python"]["path"] == "entities/python.md"
