import pytest
from pathlib import Path
from identity_server.sync import SyncManager
from identity_server.sources import SourceConfig

@pytest.fixture
def sync_manager(tmp_path):
    identity_dir = tmp_path / ".identity"
    identity_dir.mkdir()

    # Create a test source file
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "test.md").write_text("# Test Note\n\nSome content.")

    sources = [
        SourceConfig(
            name="test-notes",
            type="local_files",
            path=str(notes_dir / "*.md"),
            privacy="public",
        ),
    ]

    manager = SyncManager(identity_dir, sources)
    yield manager
    manager.close()

def test_sync_sources(sync_manager):
    results = sync_manager.sync_all()

    assert "test-notes" in results
    assert results["test-notes"]["status"] == "success"
    assert results["test-notes"]["items"] >= 1

def test_sync_updates_storage(sync_manager):
    sync_manager.sync_all()

    content = sync_manager.storage.get_content(source_name="test-notes")
    assert len(content) == 1
    assert "Test Note" in content[0].body
