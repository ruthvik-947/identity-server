# Identity MCP Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local MCP server that maintains and serves personal identity context to LLMs.

**Architecture:** FastMCP server with YAML config, SQLite storage with vector embeddings, pluggable source adapters. Core identity is curated YAML; extended context comes from periodic source scans with semantic search.

**Tech Stack:** Python 3.11+, FastMCP, SQLite + sqlite-vec, sentence-transformers, Click, PyYAML, httpx

---

## Task 1: Project Setup

**Files:**
- Create: `pyproject.toml`
- Create: `src/identity_server/__init__.py`
- Create: `src/identity_server/py.typed`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "identity-server"
version = "0.1.0"
description = "MCP server for personal identity context"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.0.0",
    "pyyaml>=6.0",
    "click>=8.0",
    "httpx>=0.27",
    "sentence-transformers>=2.2",
    "sqlite-vec>=0.1",
    "feedparser>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]

[project.scripts]
identity = "identity_server.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/identity_server"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create package structure**

```bash
mkdir -p src/identity_server tests
touch src/identity_server/__init__.py
touch src/identity_server/py.typed
touch tests/__init__.py
```

**Step 3: Create .gitignore**

```gitignore
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/
.pytest_cache/
.ruff_cache/
```

**Step 4: Install dependencies**

```bash
cd /Users/Ruthvik/projects/identity-server
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Step 5: Verify setup**

Run: `python -c "import identity_server; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add .
git commit -m "chore: initial project setup with dependencies"
```

---

## Task 2: Identity Config Schema

**Files:**
- Create: `src/identity_server/schema.py`
- Create: `tests/test_schema.py`

**Step 1: Write the failing test**

```python
# tests/test_schema.py
import pytest
from identity_server.schema import IdentityConfig, Interest

def test_identity_config_from_dict():
    data = {
        "name": "Test User",
        "background": {
            "summary": "A test user",
            "skills": ["python", "testing"],
        },
        "current_focus": ["Building things"],
        "interests": [
            {"topic": "music", "depth": "casual"},
        ],
        "privacy": {
            "public": ["name", "background"],
            "private": ["personal_notes"],
        },
    }
    config = IdentityConfig.from_dict(data)

    assert config.name == "Test User"
    assert config.background.summary == "A test user"
    assert config.background.skills == ["python", "testing"]
    assert config.current_focus == ["Building things"]
    assert len(config.interests) == 1
    assert config.interests[0].topic == "music"
    assert config.interests[0].depth == "casual"
    assert config.privacy.public == ["name", "background"]

def test_interest_depth_validation():
    with pytest.raises(ValueError):
        Interest(topic="test", depth="invalid")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL with "No module named 'identity_server.schema'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/schema.py
from dataclasses import dataclass, field
from typing import Literal

DepthLevel = Literal["casual", "engaged", "deep"]

@dataclass
class Interest:
    topic: str
    depth: DepthLevel

    def __post_init__(self):
        if self.depth not in ("casual", "engaged", "deep"):
            raise ValueError(f"Invalid depth: {self.depth}")

@dataclass
class Background:
    summary: str = ""
    skills: list[str] = field(default_factory=list)

@dataclass
class Privacy:
    public: list[str] = field(default_factory=list)
    private: list[str] = field(default_factory=list)

@dataclass
class IdentityConfig:
    name: str
    pronouns: str | None = None
    background: Background = field(default_factory=Background)
    current_focus: list[str] = field(default_factory=list)
    interests: list[Interest] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    privacy: Privacy = field(default_factory=Privacy)

    @classmethod
    def from_dict(cls, data: dict) -> "IdentityConfig":
        background = Background(**data.get("background", {}))
        privacy = Privacy(**data.get("privacy", {}))
        interests = [
            Interest(**i) for i in data.get("interests", [])
        ]
        return cls(
            name=data["name"],
            pronouns=data.get("pronouns"),
            background=background,
            current_focus=data.get("current_focus", []),
            interests=interests,
            values=data.get("values", []),
            privacy=privacy,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "pronouns": self.pronouns,
            "background": {
                "summary": self.background.summary,
                "skills": self.background.skills,
            },
            "current_focus": self.current_focus,
            "interests": [
                {"topic": i.topic, "depth": i.depth}
                for i in self.interests
            ],
            "values": self.values,
            "privacy": {
                "public": self.privacy.public,
                "private": self.privacy.private,
            },
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_schema.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/schema.py tests/test_schema.py
git commit -m "feat: add identity config schema with dataclasses"
```

---

## Task 3: Identity Loader

**Files:**
- Create: `src/identity_server/loader.py`
- Create: `tests/test_loader.py`
- Create: `tests/fixtures/identity.yaml`

**Step 1: Create test fixture**

```yaml
# tests/fixtures/identity.yaml
name: Test User
pronouns: they/them

background:
  summary: A test user for unit tests
  skills:
    - python
    - testing

current_focus:
  - Writing tests
  - Building identity server

interests:
  - topic: programming
    depth: deep

values:
  - Test-driven development

privacy:
  public:
    - name
    - background
  private:
    - personal_notes
```

**Step 2: Write the failing test**

```python
# tests/test_loader.py
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
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL with "No module named 'identity_server.loader'"

**Step 4: Write minimal implementation**

```python
# src/identity_server/loader.py
from pathlib import Path
import yaml
from .schema import IdentityConfig

def load_identity(path: Path) -> IdentityConfig:
    if not path.exists():
        raise FileNotFoundError(f"Identity file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return IdentityConfig.from_dict(data)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_loader.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/identity_server/loader.py tests/test_loader.py tests/fixtures/
git commit -m "feat: add YAML identity loader"
```

---

## Task 4: Sources Config Schema

**Files:**
- Create: `src/identity_server/sources.py`
- Create: `tests/test_sources.py`
- Create: `tests/fixtures/sources.yaml`

**Step 1: Create test fixture**

```yaml
# tests/fixtures/sources.yaml
sources:
  - name: daily-notes
    type: local_files
    path: ~/notes/**/*.md
    privacy: private

  - name: projects
    type: git_repos
    paths:
      - ~/projects/*
    extract:
      - readme
      - recent_commits
    privacy: public

  - name: reading
    type: rss
    url: https://example.com/feed.xml
    privacy: public

  - name: custom-source
    type: custom
    connector: connectors/example.py
    config:
      api_key: test
    privacy: public
```

**Step 2: Write the failing test**

```python
# tests/test_sources.py
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
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_sources.py -v`
Expected: FAIL with "No module named 'identity_server.sources'"

**Step 4: Write minimal implementation**

```python
# src/identity_server/sources.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import yaml

SourceType = Literal["local_files", "git_repos", "rss", "custom"]
PrivacyLevel = Literal["public", "private"]

@dataclass
class SourceConfig:
    name: str
    type: SourceType
    privacy: PrivacyLevel
    path: str | None = None
    paths: list[str] = field(default_factory=list)
    url: str | None = None
    extract: list[str] = field(default_factory=list)
    connector: str | None = None
    config: dict = field(default_factory=dict)

    def __post_init__(self):
        valid_types = ("local_files", "git_repos", "rss", "custom")
        if self.type not in valid_types:
            raise ValueError(f"Invalid source type: {self.type}")

def load_sources(path: Path) -> list[SourceConfig]:
    if not path.exists():
        raise FileNotFoundError(f"Sources file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return [SourceConfig(**s) for s in data.get("sources", [])]
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_sources.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/identity_server/sources.py tests/test_sources.py tests/fixtures/sources.yaml
git commit -m "feat: add sources config schema and loader"
```

---

## Task 5: SQLite Storage Layer

**Files:**
- Create: `src/identity_server/storage.py`
- Create: `tests/test_storage.py`

**Step 1: Write the failing test**

```python
# tests/test_storage.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with "No module named 'identity_server.storage'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/storage.py
import sqlite3
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class ContentItem:
    source_name: str
    title: str
    body: str
    privacy: str
    tags: list[str] = field(default_factory=list)
    timestamp: datetime | None = None
    id: str | None = None

class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                title TEXT,
                body TEXT,
                tags TEXT,
                privacy TEXT NOT NULL,
                timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_content_source
                ON content(source_name);
            CREATE INDEX IF NOT EXISTS idx_content_privacy
                ON content(privacy);

            CREATE TABLE IF NOT EXISTS sync_log (
                source_name TEXT PRIMARY KEY,
                last_sync TEXT,
                items_synced INTEGER,
                status TEXT
            );
        """)
        self.conn.commit()

    def upsert_content(self, item: ContentItem):
        item_id = item.id or f"{item.source_name}:{item.title}"
        tags_json = json.dumps(item.tags)
        timestamp = item.timestamp.isoformat() if item.timestamp else None

        self.conn.execute("""
            INSERT INTO content (id, source_name, title, body, tags, privacy, timestamp, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                body = excluded.body,
                tags = excluded.tags,
                privacy = excluded.privacy,
                timestamp = excluded.timestamp,
                updated_at = CURRENT_TIMESTAMP
        """, (item_id, item.source_name, item.title, item.body, tags_json, item.privacy, timestamp))
        self.conn.commit()

    def get_content(
        self,
        source_name: str | None = None,
        privacy: str | None = None,
        limit: int = 100,
    ) -> list[ContentItem]:
        query = "SELECT * FROM content WHERE 1=1"
        params = []

        if source_name:
            query += " AND source_name = ?"
            params.append(source_name)
        if privacy:
            query += " AND privacy = ?"
            params.append(privacy)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        return [
            ContentItem(
                id=row["id"],
                source_name=row["source_name"],
                title=row["title"],
                body=row["body"],
                tags=json.loads(row["tags"]) if row["tags"] else [],
                privacy=row["privacy"],
                timestamp=datetime.fromisoformat(row["timestamp"]) if row["timestamp"] else None,
            )
            for row in rows
        ]

    def log_sync(self, source_name: str, items_synced: int, status: str):
        self.conn.execute("""
            INSERT INTO sync_log (source_name, last_sync, items_synced, status)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            ON CONFLICT(source_name) DO UPDATE SET
                last_sync = CURRENT_TIMESTAMP,
                items_synced = excluded.items_synced,
                status = excluded.status
        """, (source_name, items_synced, status))
        self.conn.commit()

    def get_sync_log(self, source_name: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT * FROM sync_log WHERE source_name = ?",
            (source_name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        self.conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/storage.py tests/test_storage.py
git commit -m "feat: add SQLite storage layer for content"
```

---

## Task 6: Local Files Adapter

**Files:**
- Create: `src/identity_server/adapters/__init__.py`
- Create: `src/identity_server/adapters/local_files.py`
- Create: `tests/test_adapters_local.py`

**Step 1: Write the failing test**

```python
# tests/test_adapters_local.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters_local.py -v`
Expected: FAIL with "No module named 'identity_server.adapters'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/adapters/__init__.py
from .local_files import LocalFilesAdapter

__all__ = ["LocalFilesAdapter"]
```

```python
# src/identity_server/adapters/local_files.py
from datetime import datetime
from glob import glob
from pathlib import Path

from identity_server.sources import SourceConfig
from identity_server.storage import ContentItem

class LocalFilesAdapter:
    def __init__(self, config: SourceConfig):
        self.config = config
        self.path_pattern = config.path
        if self.path_pattern and self.path_pattern.startswith("~"):
            self.path_pattern = str(Path(self.path_pattern).expanduser())

    def fetch(self) -> list[ContentItem]:
        if not self.path_pattern:
            return []

        items = []
        for filepath in glob(self.path_pattern, recursive=True):
            path = Path(filepath)
            if not path.is_file():
                continue

            try:
                content = path.read_text(encoding="utf-8")
                stat = path.stat()

                items.append(ContentItem(
                    id=f"{self.config.name}:{filepath}",
                    source_name=self.config.name,
                    title=path.name,
                    body=content,
                    tags=[],
                    privacy=self.config.privacy,
                    timestamp=datetime.fromtimestamp(stat.st_mtime),
                ))
            except (IOError, UnicodeDecodeError):
                continue

        return items
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapters_local.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/adapters/ tests/test_adapters_local.py
git commit -m "feat: add local files adapter"
```

---

## Task 7: Git Repos Adapter

**Files:**
- Create: `src/identity_server/adapters/git_repos.py`
- Modify: `src/identity_server/adapters/__init__.py`
- Create: `tests/test_adapters_git.py`

**Step 1: Write the failing test**

```python
# tests/test_adapters_git.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters_git.py -v`
Expected: FAIL with "No module named 'identity_server.adapters.git_repos'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/adapters/git_repos.py
import subprocess
from datetime import datetime
from glob import glob
from pathlib import Path

from identity_server.sources import SourceConfig
from identity_server.storage import ContentItem

class GitReposAdapter:
    def __init__(self, config: SourceConfig):
        self.config = config
        self.extract = config.extract or ["readme"]

    def fetch(self) -> list[ContentItem]:
        items = []

        for pattern in self.config.paths:
            expanded = str(Path(pattern).expanduser())
            for repo_path in glob(expanded):
                repo = Path(repo_path)
                if not (repo / ".git").exists():
                    continue

                items.extend(self._extract_from_repo(repo))

        return items

    def _extract_from_repo(self, repo: Path) -> list[ContentItem]:
        items = []
        repo_name = repo.name

        if "readme" in self.extract:
            readme = self._find_readme(repo)
            if readme:
                items.append(ContentItem(
                    id=f"{self.config.name}:{repo_name}:readme",
                    source_name=self.config.name,
                    title=f"{repo_name}/README",
                    body=readme.read_text(encoding="utf-8", errors="ignore"),
                    tags=["project", repo_name],
                    privacy=self.config.privacy,
                    timestamp=datetime.fromtimestamp(readme.stat().st_mtime),
                ))

        if "recent_commits" in self.extract:
            commits = self._get_recent_commits(repo)
            if commits:
                items.append(ContentItem(
                    id=f"{self.config.name}:{repo_name}:commits",
                    source_name=self.config.name,
                    title=f"{repo_name}/recent-commits",
                    body=commits,
                    tags=["project", repo_name, "commits"],
                    privacy=self.config.privacy,
                    timestamp=datetime.now(),
                ))

        if "languages" in self.extract:
            langs = self._detect_languages(repo)
            if langs:
                items.append(ContentItem(
                    id=f"{self.config.name}:{repo_name}:languages",
                    source_name=self.config.name,
                    title=f"{repo_name}/languages",
                    body=", ".join(langs),
                    tags=["project", repo_name] + langs,
                    privacy=self.config.privacy,
                    timestamp=datetime.now(),
                ))

        return items

    def _find_readme(self, repo: Path) -> Path | None:
        for name in ["README.md", "README.txt", "README", "readme.md"]:
            readme = repo / name
            if readme.exists():
                return readme
        return None

    def _get_recent_commits(self, repo: Path, limit: int = 10) -> str:
        try:
            result = subprocess.run(
                ["git", "log", f"-{limit}", "--oneline"],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _detect_languages(self, repo: Path) -> list[str]:
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".rb": "ruby",
        }
        found = set()
        for ext, lang in extensions.items():
            if list(repo.rglob(f"*{ext}")):
                found.add(lang)
        return list(found)
```

Update `__init__.py`:

```python
# src/identity_server/adapters/__init__.py
from .local_files import LocalFilesAdapter
from .git_repos import GitReposAdapter

__all__ = ["LocalFilesAdapter", "GitReposAdapter"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapters_git.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/adapters/ tests/test_adapters_git.py
git commit -m "feat: add git repos adapter"
```

---

## Task 8: RSS Adapter

**Files:**
- Create: `src/identity_server/adapters/rss.py`
- Modify: `src/identity_server/adapters/__init__.py`
- Create: `tests/test_adapters_rss.py`

**Step 1: Write the failing test**

```python
# tests/test_adapters_rss.py
import pytest
from identity_server.adapters.rss import RSSAdapter
from identity_server.sources import SourceConfig

# We'll mock feedparser for testing
def test_rss_adapter_parse_entries(mocker):
    mock_feed = mocker.MagicMock()
    mock_feed.entries = [
        mocker.MagicMock(
            title="Article 1",
            summary="Summary of article 1",
            link="https://example.com/1",
            published_parsed=(2024, 1, 15, 12, 0, 0, 0, 0, 0),
        ),
        mocker.MagicMock(
            title="Article 2",
            summary="Summary of article 2",
            link="https://example.com/2",
            published_parsed=(2024, 1, 16, 12, 0, 0, 0, 0, 0),
        ),
    ]

    mocker.patch("feedparser.parse", return_value=mock_feed)

    config = SourceConfig(
        name="reading",
        type="rss",
        url="https://example.com/feed.xml",
        privacy="public",
    )
    adapter = RSSAdapter(config)
    items = adapter.fetch()

    assert len(items) == 2
    assert items[0].title == "Article 1"
    assert "Summary of article 1" in items[0].body
```

**Step 2: Run test to verify it fails**

Run: `pip install pytest-mock && pytest tests/test_adapters_rss.py -v`
Expected: FAIL with "No module named 'identity_server.adapters.rss'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/adapters/rss.py
from datetime import datetime
from time import mktime

import feedparser

from identity_server.sources import SourceConfig
from identity_server.storage import ContentItem

class RSSAdapter:
    def __init__(self, config: SourceConfig):
        self.config = config
        self.url = config.url

    def fetch(self) -> list[ContentItem]:
        if not self.url:
            return []

        feed = feedparser.parse(self.url)
        items = []

        for entry in feed.entries:
            timestamp = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                timestamp = datetime.fromtimestamp(mktime(entry.published_parsed))

            body = getattr(entry, "summary", "") or getattr(entry, "description", "")
            link = getattr(entry, "link", "")

            items.append(ContentItem(
                id=f"{self.config.name}:{link or entry.title}",
                source_name=self.config.name,
                title=entry.title,
                body=f"{body}\n\nLink: {link}" if link else body,
                tags=["rss"],
                privacy=self.config.privacy,
                timestamp=timestamp,
            ))

        return items
```

Update `__init__.py`:

```python
# src/identity_server/adapters/__init__.py
from .local_files import LocalFilesAdapter
from .git_repos import GitReposAdapter
from .rss import RSSAdapter

__all__ = ["LocalFilesAdapter", "GitReposAdapter", "RSSAdapter"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapters_rss.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/adapters/ tests/test_adapters_rss.py
git commit -m "feat: add RSS feed adapter"
```

---

## Task 9: Custom Adapter Loader

**Files:**
- Create: `src/identity_server/adapters/custom.py`
- Modify: `src/identity_server/adapters/__init__.py`
- Create: `tests/test_adapters_custom.py`

**Step 1: Write the failing test**

```python
# tests/test_adapters_custom.py
import pytest
from pathlib import Path
from identity_server.adapters.custom import CustomAdapter
from identity_server.sources import SourceConfig

@pytest.fixture
def custom_connector(tmp_path):
    connector = tmp_path / "connectors" / "test_connector.py"
    connector.parent.mkdir(parents=True)
    connector.write_text('''
def fetch(config):
    return [
        {"title": "Custom Item 1", "body": "Content 1", "tags": ["test"]},
        {"title": "Custom Item 2", "body": "Content 2", "tags": ["test"]},
    ]
''')
    return connector

def test_custom_adapter_loads_connector(custom_connector, tmp_path):
    config = SourceConfig(
        name="custom-test",
        type="custom",
        connector=str(custom_connector),
        config={"key": "value"},
        privacy="public",
    )
    adapter = CustomAdapter(config, base_path=tmp_path)
    items = adapter.fetch()

    assert len(items) == 2
    assert items[0].title == "Custom Item 1"
    assert items[0].source_name == "custom-test"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters_custom.py -v`
Expected: FAIL with "No module named 'identity_server.adapters.custom'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/adapters/custom.py
import importlib.util
from pathlib import Path

from identity_server.sources import SourceConfig
from identity_server.storage import ContentItem

class CustomAdapter:
    def __init__(self, config: SourceConfig, base_path: Path | None = None):
        self.config = config
        self.base_path = base_path or Path.home() / ".identity"
        self.connector_path = self._resolve_connector_path()

    def _resolve_connector_path(self) -> Path:
        if not self.config.connector:
            raise ValueError("Custom adapter requires 'connector' path")

        path = Path(self.config.connector)
        if path.is_absolute():
            return path
        return self.base_path / path

    def fetch(self) -> list[ContentItem]:
        if not self.connector_path.exists():
            raise FileNotFoundError(f"Connector not found: {self.connector_path}")

        # Dynamically load the connector module
        spec = importlib.util.spec_from_file_location(
            f"connector_{self.config.name}",
            self.connector_path,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "fetch"):
            raise ValueError(f"Connector must define a 'fetch' function: {self.connector_path}")

        # Call the connector's fetch function
        raw_items = module.fetch(self.config.config)

        # Convert to ContentItems
        items = []
        for item in raw_items:
            items.append(ContentItem(
                id=f"{self.config.name}:{item.get('title', 'untitled')}",
                source_name=self.config.name,
                title=item.get("title", "Untitled"),
                body=item.get("body", ""),
                tags=item.get("tags", []),
                privacy=self.config.privacy,
                timestamp=item.get("timestamp"),
            ))

        return items
```

Update `__init__.py`:

```python
# src/identity_server/adapters/__init__.py
from .local_files import LocalFilesAdapter
from .git_repos import GitReposAdapter
from .rss import RSSAdapter
from .custom import CustomAdapter

__all__ = ["LocalFilesAdapter", "GitReposAdapter", "RSSAdapter", "CustomAdapter"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapters_custom.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/adapters/ tests/test_adapters_custom.py
git commit -m "feat: add custom adapter loader"
```

---

## Task 10: Embeddings & Vector Search

**Files:**
- Create: `src/identity_server/embeddings.py`
- Create: `tests/test_embeddings.py`

**Step 1: Write the failing test**

```python
# tests/test_embeddings.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_embeddings.py -v`
Expected: FAIL with "No module named 'identity_server.embeddings'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/embeddings.py
import json
import sqlite3
from pathlib import Path

import sqlite_vec
from sentence_transformers import SentenceTransformer

from identity_server.storage import ContentItem

class EmbeddingIndex:
    def __init__(self, db_path: Path, model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        self._init_tables()

    def _init_tables(self):
        self.conn.executescript(f"""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                source_name TEXT,
                title TEXT,
                body TEXT,
                privacy TEXT,
                embedding BLOB
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS vec_embeddings USING vec0(
                id TEXT PRIMARY KEY,
                embedding float[{self.embedding_dim}]
            );
        """)
        self.conn.commit()

    def index_item(self, item: ContentItem):
        text = f"{item.title}\n\n{item.body}"
        embedding = self.model.encode(text)
        embedding_bytes = embedding.tobytes()

        # Store metadata
        self.conn.execute("""
            INSERT OR REPLACE INTO embeddings (id, source_name, title, body, privacy, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item.id, item.source_name, item.title, item.body, item.privacy, embedding_bytes))

        # Store vector for search
        self.conn.execute("""
            INSERT OR REPLACE INTO vec_embeddings (id, embedding)
            VALUES (?, ?)
        """, (item.id, embedding_bytes))

        self.conn.commit()

    def search(
        self,
        query: str,
        top_k: int = 5,
        privacy: str | None = None,
    ) -> list[ContentItem]:
        query_embedding = self.model.encode(query)
        query_bytes = query_embedding.tobytes()

        # Vector similarity search
        cursor = self.conn.execute("""
            SELECT id, distance
            FROM vec_embeddings
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
        """, (query_bytes, top_k * 2))  # Get more to filter by privacy

        results = []
        for row in cursor.fetchall():
            # Get full metadata
            meta = self.conn.execute(
                "SELECT * FROM embeddings WHERE id = ?",
                (row["id"],)
            ).fetchone()

            if meta and (privacy is None or meta["privacy"] == privacy):
                results.append(ContentItem(
                    id=meta["id"],
                    source_name=meta["source_name"],
                    title=meta["title"],
                    body=meta["body"],
                    privacy=meta["privacy"],
                ))

            if len(results) >= top_k:
                break

        return results

    def close(self):
        self.conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_embeddings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/embeddings.py tests/test_embeddings.py
git commit -m "feat: add embedding index with vector search"
```

---

## Task 11: Sync Manager

**Files:**
- Create: `src/identity_server/sync.py`
- Create: `tests/test_sync.py`

**Step 1: Write the failing test**

```python
# tests/test_sync.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py -v`
Expected: FAIL with "No module named 'identity_server.sync'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/sync.py
from pathlib import Path

from identity_server.adapters import (
    LocalFilesAdapter,
    GitReposAdapter,
    RSSAdapter,
    CustomAdapter,
)
from identity_server.embeddings import EmbeddingIndex
from identity_server.sources import SourceConfig
from identity_server.storage import Storage

class SyncManager:
    def __init__(self, identity_dir: Path, sources: list[SourceConfig]):
        self.identity_dir = identity_dir
        self.sources = sources

        self.storage = Storage(identity_dir / "index.db")
        self.embeddings = EmbeddingIndex(identity_dir / "embeddings.db")

    def sync_all(self) -> dict:
        results = {}

        for source in self.sources:
            try:
                items = self._fetch_source(source)

                for item in items:
                    self.storage.upsert_content(item)
                    self.embeddings.index_item(item)

                self.storage.log_sync(source.name, len(items), "success")
                results[source.name] = {"status": "success", "items": len(items)}

            except Exception as e:
                self.storage.log_sync(source.name, 0, f"error: {e}")
                results[source.name] = {"status": "error", "error": str(e)}

        return results

    def sync_source(self, source_name: str) -> dict:
        source = next((s for s in self.sources if s.name == source_name), None)
        if not source:
            return {"status": "error", "error": f"Source not found: {source_name}"}

        try:
            items = self._fetch_source(source)

            for item in items:
                self.storage.upsert_content(item)
                self.embeddings.index_item(item)

            self.storage.log_sync(source.name, len(items), "success")
            return {"status": "success", "items": len(items)}

        except Exception as e:
            self.storage.log_sync(source.name, 0, f"error: {e}")
            return {"status": "error", "error": str(e)}

    def _fetch_source(self, source: SourceConfig):
        adapter_map = {
            "local_files": LocalFilesAdapter,
            "git_repos": GitReposAdapter,
            "rss": RSSAdapter,
            "custom": lambda c: CustomAdapter(c, self.identity_dir),
        }

        adapter_cls = adapter_map.get(source.type)
        if not adapter_cls:
            raise ValueError(f"Unknown source type: {source.type}")

        adapter = adapter_cls(source)
        return adapter.fetch()

    def close(self):
        self.storage.close()
        self.embeddings.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sync.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/sync.py tests/test_sync.py
git commit -m "feat: add sync manager for coordinating source updates"
```

---

## Task 12: MCP Server Core

**Files:**
- Create: `src/identity_server/server.py`
- Create: `tests/test_server.py`

**Step 1: Write the failing test**

```python
# tests/test_server.py
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

def test_server_has_tools(identity_dir):
    server = create_server(identity_dir)
    tool_names = [t.name for t in server.list_tools()]

    assert "get_identity" in tool_names
    assert "get_projects" in tool_names
    assert "query" in tool_names
    assert "list_sources" in tool_names
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_server.py -v`
Expected: FAIL with "No module named 'identity_server.server'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/server.py
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from identity_server.loader import load_identity
from identity_server.sources import load_sources
from identity_server.storage import Storage
from identity_server.embeddings import EmbeddingIndex
from identity_server.sync import SyncManager

def create_server(identity_dir: Path) -> Server:
    server = Server("identity-server")

    # Load configs
    identity_path = identity_dir / "identity.yaml"
    sources_path = identity_dir / "sources.yaml"

    identity = load_identity(identity_path) if identity_path.exists() else None
    sources = load_sources(sources_path) if sources_path.exists() else []

    # Initialize storage
    storage = Storage(identity_dir / "index.db")
    embeddings = EmbeddingIndex(identity_dir / "embeddings.db")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_identity",
                description="Get core identity info: background, skills, current focus, interests",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="get_projects",
                description="Get projects. Status: 'active', 'recent', or 'all'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["active", "recent", "all"]},
                    },
                },
            ),
            Tool(
                name="get_reading",
                description="Get recent reading list items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            ),
            Tool(
                name="query",
                description="Natural language query across all indexed content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "sources": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["question"],
                },
            ),
            Tool(
                name="list_sources",
                description="List configured sources and their last sync time",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="add_source",
                description="Get instructions for adding a new source",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                    },
                    "required": ["description"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "get_identity":
            if not identity:
                return [TextContent(type="text", text="No identity configured")]
            return [TextContent(type="text", text=_format_identity(identity))]

        elif name == "get_projects":
            status = arguments.get("status", "active")
            content = storage.get_content(source_name="projects", limit=50)
            return [TextContent(type="text", text=_format_projects(content))]

        elif name == "get_reading":
            limit = arguments.get("limit", 20)
            content = storage.get_content(limit=limit)
            reading = [c for c in content if "rss" in c.tags]
            return [TextContent(type="text", text=_format_reading(reading))]

        elif name == "query":
            question = arguments["question"]
            results = embeddings.search(question, top_k=5, privacy="public")
            return [TextContent(type="text", text=_format_search_results(question, results))]

        elif name == "list_sources":
            source_info = []
            for s in sources:
                log = storage.get_sync_log(s.name)
                source_info.append({
                    "name": s.name,
                    "type": s.type,
                    "privacy": s.privacy,
                    "last_sync": log["last_sync"] if log else "never",
                })
            return [TextContent(type="text", text=_format_sources(source_info))]

        elif name == "add_source":
            desc = arguments["description"]
            return [TextContent(type="text", text=_add_source_instructions(desc))]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server

def _format_identity(identity) -> str:
    lines = [
        f"# {identity.name}",
        "",
        f"**Background:** {identity.background.summary}",
        f"**Skills:** {', '.join(identity.background.skills)}",
        "",
        "**Current Focus:**",
    ]
    for focus in identity.current_focus:
        lines.append(f"- {focus}")

    lines.append("")
    lines.append("**Interests:**")
    for interest in identity.interests:
        lines.append(f"- {interest.topic} ({interest.depth})")

    if identity.values:
        lines.append("")
        lines.append("**Values:**")
        for value in identity.values:
            lines.append(f"- {value}")

    return "\n".join(lines)

def _format_projects(content) -> str:
    if not content:
        return "No projects indexed yet."

    lines = ["# Projects", ""]
    for item in content:
        lines.append(f"## {item.title}")
        lines.append(item.body[:500])
        lines.append("")

    return "\n".join(lines)

def _format_reading(content) -> str:
    if not content:
        return "No reading items indexed yet."

    lines = ["# Recent Reading", ""]
    for item in content:
        lines.append(f"- **{item.title}**")
        if item.body:
            lines.append(f"  {item.body[:200]}...")
        lines.append("")

    return "\n".join(lines)

def _format_search_results(question: str, results) -> str:
    if not results:
        return f"No results found for: {question}"

    lines = [f"# Results for: {question}", ""]
    for item in results:
        lines.append(f"## {item.title} (from {item.source_name})")
        lines.append(item.body[:500])
        lines.append("")

    return "\n".join(lines)

def _format_sources(sources) -> str:
    if not sources:
        return "No sources configured."

    lines = ["# Configured Sources", ""]
    for s in sources:
        lines.append(f"- **{s['name']}** ({s['type']}, {s['privacy']})")
        lines.append(f"  Last sync: {s['last_sync']}")

    return "\n".join(lines)

def _add_source_instructions(description: str) -> str:
    return f"""To add a source like "{description}", edit ~/.identity/sources.yaml.

**Built-in types:**
- `local_files`: path glob (e.g., ~/notes/**/*.md)
- `git_repos`: paths to repos
- `rss`: feed URL
- `custom`: Python script connector

**Example:**
```yaml
sources:
  - name: my-source
    type: rss
    url: https://example.com/feed.xml
    privacy: public
```

For custom sources, create a connector in ~/.identity/connectors/ with a `fetch(config)` function.
"""

async def run_server(identity_dir: Path):
    server = create_server(identity_dir)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_server.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/server.py tests/test_server.py
git commit -m "feat: add MCP server with identity tools"
```

---

## Task 13: CLI Interface

**Files:**
- Create: `src/identity_server/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
# tests/test_cli.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with "No module named 'identity_server.cli'"

**Step 3: Write minimal implementation**

```python
# src/identity_server/cli.py
import asyncio
import os
from pathlib import Path

import click

from identity_server.loader import load_identity
from identity_server.sources import load_sources
from identity_server.sync import SyncManager
from identity_server.server import run_server

def get_identity_dir() -> Path:
    return Path(os.environ.get("IDENTITY_DIR", Path.home() / ".identity"))

@click.group()
def main():
    """Identity server CLI - manage your personal identity context."""
    pass

@main.command()
def status():
    """Show current identity status."""
    identity_dir = get_identity_dir()

    identity_path = identity_dir / "identity.yaml"
    if not identity_path.exists():
        click.echo(f"No identity configured at {identity_path}")
        return

    identity = load_identity(identity_path)

    click.echo(f"Name: {identity.name}")
    click.echo(f"Background: {identity.background.summary}")
    click.echo(f"Skills: {', '.join(identity.background.skills)}")
    click.echo(f"Current focus: {', '.join(identity.current_focus)}")

@main.command()
@click.option("--source", "-s", help="Sync specific source only")
def sync(source: str | None):
    """Sync all sources or a specific source."""
    identity_dir = get_identity_dir()

    sources_path = identity_dir / "sources.yaml"
    if not sources_path.exists():
        click.echo(f"No sources configured at {sources_path}")
        return

    sources = load_sources(sources_path)
    manager = SyncManager(identity_dir, sources)

    try:
        if source:
            result = manager.sync_source(source)
            click.echo(f"{source}: {result['status']} ({result.get('items', 0)} items)")
        else:
            results = manager.sync_all()
            for name, result in results.items():
                status = result["status"]
                items = result.get("items", 0)
                click.echo(f"{name}: {status} ({items} items)")

        click.echo("\nSync complete!")
    finally:
        manager.close()

@main.command()
def sources():
    """List configured sources."""
    identity_dir = get_identity_dir()

    sources_path = identity_dir / "sources.yaml"
    if not sources_path.exists():
        click.echo(f"No sources configured at {sources_path}")
        return

    sources = load_sources(sources_path)

    if not sources:
        click.echo("No sources configured.")
        return

    for s in sources:
        click.echo(f"- {s.name} ({s.type}, {s.privacy})")

@main.command()
@click.option("--init", is_flag=True, help="Initialize identity directory")
def init(init: bool):
    """Initialize identity directory with example files."""
    identity_dir = get_identity_dir()

    if identity_dir.exists() and not init:
        click.echo(f"Identity directory exists at {identity_dir}")
        click.echo("Use --init to reinitialize.")
        return

    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / "connectors").mkdir(exist_ok=True)

    # Create example identity.yaml
    identity_example = """# Your identity - edit this file!
name: Your Name
pronouns: they/them  # optional

background:
  summary: A brief description of who you are
  skills:
    - python
    - javascript

current_focus:
  - What you're currently working on

interests:
  - topic: programming
    depth: deep  # casual, engaged, or deep

values:
  - Things you care about

privacy:
  public:
    - name
    - background
    - interests
  private:
    - personal_notes
"""

    # Create example sources.yaml
    sources_example = """# Data sources to index
sources:
  # Example: local markdown files
  # - name: notes
  #   type: local_files
  #   path: ~/notes/**/*.md
  #   privacy: private

  # Example: git repositories
  # - name: projects
  #   type: git_repos
  #   paths:
  #     - ~/projects/*
  #   extract:
  #     - readme
  #     - recent_commits
  #   privacy: public
"""

    (identity_dir / "identity.yaml").write_text(identity_example)
    (identity_dir / "sources.yaml").write_text(sources_example)

    click.echo(f"Initialized identity directory at {identity_dir}")
    click.echo("Edit identity.yaml and sources.yaml to configure.")

@main.command()
def serve():
    """Start the MCP server."""
    identity_dir = get_identity_dir()

    if not (identity_dir / "identity.yaml").exists():
        click.echo(f"No identity configured. Run 'identity init' first.")
        return

    click.echo(f"Starting identity server from {identity_dir}")
    asyncio.run(run_server(identity_dir))

if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/identity_server/cli.py tests/test_cli.py
git commit -m "feat: add CLI interface for identity management"
```

---

## Task 14: Integration Test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write the integration test**

```python
# tests/test_integration.py
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
    assert "Integration Test User" in identity_result[0].text
    assert "python" in identity_result[0].text

    # Test query (semantic search)
    query_result = await server.call_tool("query", {
        "question": "What work was done on MCP?"
    })
    assert "MCP" in query_result[0].text or "mcp" in query_result[0].text.lower()

    # Test list_sources
    sources_result = await server.call_tool("list_sources", {})
    assert "daily-notes" in sources_result[0].text

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
    from identity_server.sources import load_sources, SourceConfig
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
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full workflow"
```

---

## Task 15: Documentation & Final Setup

**Files:**
- Create: `README.md`
- Create: `~/.identity/` example structure

**Step 1: Create README**

```markdown
# Identity Server

A local MCP server that maintains and serves personal identity context to LLMs.

## Installation

```bash
pip install -e .
```

## Quick Start

1. Initialize your identity directory:

```bash
identity init
```

2. Edit `~/.identity/identity.yaml` with your info

3. Configure sources in `~/.identity/sources.yaml`

4. Sync your sources:

```bash
identity sync
```

5. Add to Claude Code's MCP config:

```json
{
  "mcpServers": {
    "identity": {
      "command": "identity",
      "args": ["serve"]
    }
  }
}
```

## CLI Commands

- `identity init` - Initialize identity directory
- `identity status` - Show current identity
- `identity sync` - Sync all sources
- `identity sources` - List configured sources
- `identity serve` - Start MCP server

## MCP Tools

- `get_identity()` - Core identity info
- `get_projects()` - Indexed projects
- `get_reading()` - Reading list items
- `query(question)` - Semantic search
- `list_sources()` - Configured sources
- `add_source(description)` - Setup instructions

## Source Types

- `local_files` - Markdown/text files via glob
- `git_repos` - README, commits, languages
- `rss` - RSS/Atom feeds
- `custom` - Python script connectors

## Privacy

Tag sources as `public` or `private`. Private content is excluded from MCP queries.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage instructions"
```

---

## Summary

**Total tasks:** 15
**Estimated implementation:** Follows TDD throughout

**Key checkpoints:**
- After Task 6: Core adapters working
- After Task 10: Full storage + search
- After Task 12: MCP server functional
- After Task 14: Integration tested

**To run all tests:**
```bash
pytest tests/ -v
```

**To start the server:**
```bash
identity serve
```
