import pytest
from pathlib import Path
from identity_server.server import create_server
from identity_server.sync import SyncManager
from identity_server.sources import SourceConfig

@pytest.fixture
def full_setup(tmp_path):
    """Set up a complete identity environment for testing."""
    identity_dir = tmp_path / ".identity"
    identity_dir.mkdir()
    (identity_dir / "connectors").mkdir()

    # Create identity
    (identity_dir / "identity.yaml").write_text("""
name: Integration Test User
pronouns: they/them

background:
  summary: A developer who loves testing
  skills:
    - python
    - testing
    - mcp

current_focus:
  - Building identity server
  - Writing integration tests

interests:
  - topic: distributed-systems
    depth: deep
  - topic: llms
    depth: engaged

values:
  - Test everything
  - Keep it simple

privacy:
  public:
    - name
    - background
    - interests
  private:
    - personal_notes
""")

    # Create notes directory with content
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "2024-01-01.md").write_text("""
# Daily Note - Jan 1

Worked on the identity server project today.
Key decisions:
- Use SQLite for storage
- sentence-transformers for embeddings
- FastMCP for the server

TODO: Write more tests!
""")
    (notes_dir / "2024-01-02.md").write_text("""
# Daily Note - Jan 2

Continued work on MCP tools.
The query tool is working well with semantic search.
""")

    # Create sources config
    (identity_dir / "sources.yaml").write_text(f"""
sources:
  - name: daily-notes
    type: local_files
    path: {notes_dir}/*.md
    privacy: public
""")

    return identity_dir

@pytest.mark.asyncio
async def test_full_workflow(full_setup):
    """Test the complete workflow: sync -> query -> get_identity."""
    identity_dir = full_setup

    # Load and sync sources
    from identity_server.sources import load_sources
    sources = load_sources(identity_dir / "sources.yaml")

    manager = SyncManager(identity_dir, sources)
    results = manager.sync_all()

    assert results["daily-notes"]["status"] == "success"
    assert results["daily-notes"]["items"] == 2

    # Create server and test tools
    server = create_server(identity_dir)

    # Test get_identity
    identity_result = await server.call_tool("get_identity", {})
    assert "Integration Test User" in str(identity_result)
    assert "python" in str(identity_result)

    # Test query (semantic search)
    query_result = await server.call_tool("query", {
        "question": "What work was done on MCP?"
    })
    assert "MCP" in str(query_result) or "mcp" in str(query_result).lower()

    # Test list_sources
    sources_result = await server.call_tool("list_sources", {})
    assert "daily-notes" in str(sources_result)

    manager.close()

@pytest.mark.asyncio
async def test_privacy_filtering(full_setup):
    """Test that private content is filtered from queries."""
    identity_dir = full_setup

    # Add private source
    private_dir = identity_dir.parent / "private_notes"
    private_dir.mkdir()
    (private_dir / "secret.md").write_text("SECRET: My password is hunter2")

    # Update sources to include private
    from identity_server.sources import SourceConfig
    sources = [
        SourceConfig(
            name="public-notes",
            type="local_files",
            path=str(identity_dir.parent / "notes" / "*.md"),
            privacy="public",
        ),
        SourceConfig(
            name="private-notes",
            type="local_files",
            path=str(private_dir / "*.md"),
            privacy="private",
        ),
    ]

    manager = SyncManager(identity_dir, sources)
    manager.sync_all()

    # Query should not return private content
    from identity_server.embeddings import EmbeddingIndex
    embeddings = EmbeddingIndex(identity_dir / "embeddings.db")

    results = embeddings.search("password", top_k=5, privacy="public")

    # Should not find the private note
    for result in results:
        assert "hunter2" not in result.body
        assert result.privacy == "public"

    manager.close()
    embeddings.close()
