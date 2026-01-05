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
