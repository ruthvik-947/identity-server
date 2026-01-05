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
