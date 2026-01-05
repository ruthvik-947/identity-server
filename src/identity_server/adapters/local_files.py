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
