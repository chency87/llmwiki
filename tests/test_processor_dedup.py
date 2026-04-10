from pathlib import Path
from llmwiki.ingest.processor import Processor

def test_processor_skips_unchanged_file(tmp_path: Path) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("first version", encoding="utf-8")

    vault_path = tmp_path / "vault"
    processor = Processor(vault_path=str(vault_path))

    dest_path, extracted_text, needs_processing = processor.process_file(str(source_file))
    assert needs_processing is True
    assert extracted_text == "first version"

    processor.mark_as_done(dest_path)

    _, extracted_text_again, needs_processing_again = processor.process_file(str(source_file))
    assert needs_processing_again is False
    assert extracted_text_again is None

def test_processor_reprocesses_modified_file(tmp_path: Path) -> None:
    source_file = tmp_path / "source.txt"
    source_file.write_text("v1", encoding="utf-8")

    vault_path = tmp_path / "vault"
    processor = Processor(vault_path=str(vault_path))

    dest_path, _, first_needs_processing = processor.process_file(str(source_file))
    assert first_needs_processing is True
    processor.mark_as_done(dest_path)

    source_file.write_text("v2", encoding="utf-8")

    _, extracted_text, second_needs_processing = processor.process_file(str(source_file))
    assert second_needs_processing is True
    assert extracted_text == "v2"
