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
