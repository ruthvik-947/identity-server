import pytest
from click.testing import CliRunner
from pathlib import Path
from identity_server.cli import main

@pytest.fixture
def identity_dir(tmp_path, monkeypatch):
    d = tmp_path / ".identity"
    d.mkdir()

    (d / "identity.yaml").write_text("""
name: Test User
background:
  summary: A test user
  skills: [python]
""")

    (d / "sources.yaml").write_text("""
sources: []
""")

    monkeypatch.setenv("IDENTITY_DIR", str(d))
    return d

def test_cli_status(identity_dir):
    runner = CliRunner()
    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "Test User" in result.output

def test_cli_sync(identity_dir):
    runner = CliRunner()
    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "Sync complete" in result.output

def test_cli_sources(identity_dir):
    runner = CliRunner()
    result = runner.invoke(main, ["sources"])

    assert result.exit_code == 0
