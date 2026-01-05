import pytest
from pathlib import Path
from identity_server.storage import Storage, ContentItem

@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test.db"
    s = Storage(db_path)
    yield s
    s.close()

def test_storage_init_creates_tables(storage):
    # Tables should exist after init
    cursor = storage.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "content" in tables
    assert "sync_log" in tables

def test_upsert_and_get_content(storage):
    item = ContentItem(
        source_name="test-source",
        title="Test Item",
        body="This is test content",
        tags=["test", "example"],
        privacy="public",
    )
    storage.upsert_content(item)

    results = storage.get_content(source_name="test-source")
    assert len(results) == 1
    assert results[0].title == "Test Item"
    assert results[0].tags == ["test", "example"]

def test_get_content_filters_by_privacy(storage):
    storage.upsert_content(ContentItem(
        source_name="s1", title="Public", body="", privacy="public"
    ))
    storage.upsert_content(ContentItem(
        source_name="s1", title="Private", body="", privacy="private"
    ))

    public = storage.get_content(privacy="public")
    assert len(public) == 1
    assert public[0].title == "Public"

def test_log_sync(storage):
    storage.log_sync("test-source", items_synced=5, status="success")

    log = storage.get_sync_log("test-source")
    assert log is not None
    assert log["items_synced"] == 5
    assert log["status"] == "success"
