import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse


class Database:
    def __init__(self, database_url: str) -> None:
        parsed = urlparse(database_url)
        if parsed.scheme != "sqlite":
            raise ValueError("Only sqlite:// URLs are supported by this prototype")
        raw_path = unquote(parsed.path)
        if raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
            raw_path = raw_path[1:]
        elif raw_path.startswith("/./"):
            raw_path = raw_path[1:]
        self.path = Path(raw_path if not parsed.netloc else f"//{parsed.netloc}{raw_path}")
        if str(self.path) in ("", "."):
            self.path = Path("./data/app.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    slug TEXT PRIMARY KEY,
                    target_url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    clicks INTEGER NOT NULL DEFAULT 0,
                    last_accessed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    scenario TEXT NOT NULL,
                    status TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )


