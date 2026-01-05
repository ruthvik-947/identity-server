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
