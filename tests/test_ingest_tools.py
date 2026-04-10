from llmwiki.ingest.extractors.registry import registry
from llmwiki.ingest.manifest import Manifest

def test_extractor_text(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")
    text = registry.extract(str(test_file))
    assert text == "hello world"

def test_extractor_unsupported():
    assert registry.extract("nonexistent.xyz") is None

def test_manifest_integration(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    manifest = Manifest(vault_path=str(vault))
    
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    file_hash = manifest.get_file_hash(str(test_file))
    
    assert manifest.is_processed("test.txt", file_hash) is None
    manifest.mark_processed("test.txt", file_hash)
    assert manifest.is_processed("test.txt", file_hash) is True
