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
