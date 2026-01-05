import pytest
from pathlib import Path
from identity_server.embeddings import EmbeddingIndex
from identity_server.storage import ContentItem

@pytest.fixture
def embedding_index(tmp_path):
    db_path = tmp_path / "test.db"
    index = EmbeddingIndex(db_path)
    yield index
    index.close()

def test_index_and_search(embedding_index):
    items = [
        ContentItem(
            id="1",
            source_name="test",
            title="Python Programming",
            body="Python is a great language for machine learning and data science.",
            privacy="public",
        ),
        ContentItem(
            id="2",
            source_name="test",
            title="Cooking Recipe",
            body="To make pasta, boil water and add noodles for 10 minutes.",
            privacy="public",
        ),
        ContentItem(
            id="3",
            source_name="test",
            title="TypeScript Guide",
            body="TypeScript adds static typing to JavaScript for better development.",
            privacy="public",
        ),
    ]

    for item in items:
        embedding_index.index_item(item)

    # Search for programming-related content
    results = embedding_index.search("programming languages", top_k=2)

    assert len(results) == 2
    titles = [r.title for r in results]
    assert "Python Programming" in titles
    assert "TypeScript Guide" in titles
    assert "Cooking Recipe" not in titles
