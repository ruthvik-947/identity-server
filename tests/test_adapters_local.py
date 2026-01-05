import pytest
from pathlib import Path
from identity_server.adapters.local_files import LocalFilesAdapter
from identity_server.sources import SourceConfig

@pytest.fixture
def notes_dir(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()

    (notes / "2024-01-01.md").write_text("# Daily Note\n\nWorked on project X.")
    (notes / "2024-01-02.md").write_text("# Another Note\n\nLearned about Y.")
    (notes / "subdir").mkdir()
    (notes / "subdir" / "deep.md").write_text("# Deep Note\n\nNested content.")

    return notes

def test_local_files_adapter_fetch(notes_dir):
    config = SourceConfig(
        name="notes",
        type="local_files",
        path=str(notes_dir / "**/*.md"),
        privacy="private",
    )
    adapter = LocalFilesAdapter(config)
    items = adapter.fetch()

    assert len(items) == 3
    titles = {item.title for item in items}
    assert "2024-01-01.md" in titles
    assert "deep.md" in titles

def test_local_files_adapter_search(notes_dir):
    config = SourceConfig(
        name="notes",
        type="local_files",
        path=str(notes_dir / "**/*.md"),
        privacy="private",
    )
    adapter = LocalFilesAdapter(config)
    items = adapter.fetch()

    # Search for "project"
    results = [i for i in items if "project" in i.body.lower()]
    assert len(results) == 1
    assert "2024-01-01" in results[0].title
