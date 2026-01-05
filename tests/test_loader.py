import pytest
from pathlib import Path
from identity_server.loader import load_identity

FIXTURES = Path(__file__).parent / "fixtures"

def test_load_identity_from_yaml():
    config = load_identity(FIXTURES / "identity.yaml")

    assert config.name == "Test User"
    assert config.pronouns == "they/them"
    assert "python" in config.background.skills

def test_load_identity_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_identity(Path("/nonexistent/identity.yaml"))
