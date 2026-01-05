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
