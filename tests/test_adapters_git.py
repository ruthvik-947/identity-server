import pytest
import subprocess
from pathlib import Path
from identity_server.adapters.git_repos import GitReposAdapter
from identity_server.sources import SourceConfig

@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Init repo
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)

    # Create README
    (repo / "README.md").write_text("# Test Repo\n\nThis is a test project.")

    # Make commit
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, capture_output=True)

    return repo

def test_git_repos_adapter_fetch(git_repo, tmp_path):
    config = SourceConfig(
        name="projects",
        type="git_repos",
        paths=[str(tmp_path / "*")],
        extract=["readme", "recent_commits"],
        privacy="public",
    )
    adapter = GitReposAdapter(config)
    items = adapter.fetch()

    assert len(items) >= 1
    readme_item = next((i for i in items if "README" in i.title), None)
    assert readme_item is not None
    assert "test project" in readme_item.body.lower()
