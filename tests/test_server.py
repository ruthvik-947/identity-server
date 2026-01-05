import pytest
from pathlib import Path
from identity_server.server import create_server

@pytest.fixture
def identity_dir(tmp_path):
    d = tmp_path / ".identity"
    d.mkdir()

    # Create identity.yaml
    (d / "identity.yaml").write_text("""
name: Test User
background:
  summary: A test user
  skills: [python, testing]
current_focus:
  - Building identity server
interests:
  - topic: programming
    depth: deep
privacy:
  public: [name, background]
  private: [personal_notes]
""")

    # Create sources.yaml
    (d / "sources.yaml").write_text("""
sources: []
""")

    return d

def test_create_server(identity_dir):
    server = create_server(identity_dir)
    assert server is not None
    assert server.name == "identity-server"

@pytest.mark.asyncio
async def test_server_has_tools(identity_dir):
    server = create_server(identity_dir)
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]

    assert "get_identity" in tool_names
    assert "get_projects" in tool_names
    assert "query" in tool_names
    assert "list_sources" in tool_names
