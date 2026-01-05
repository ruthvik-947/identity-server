import pytest
from pathlib import Path
from identity_server.sources import SourceConfig, load_sources

FIXTURES = Path(__file__).parent / "fixtures"

def test_load_sources():
    sources = load_sources(FIXTURES / "sources.yaml")

    assert len(sources) == 4

    notes = sources[0]
    assert notes.name == "daily-notes"
    assert notes.type == "local_files"
    assert notes.privacy == "private"

    projects = sources[1]
    assert projects.type == "git_repos"
    assert "readme" in projects.extract

    custom = sources[3]
    assert custom.type == "custom"
    assert custom.connector == "connectors/example.py"

def test_source_config_type_validation():
    with pytest.raises(ValueError):
        SourceConfig(name="test", type="invalid", privacy="public")
