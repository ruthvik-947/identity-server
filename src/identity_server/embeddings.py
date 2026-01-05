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
