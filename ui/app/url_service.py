import secrets
import string
from datetime import UTC, datetime

from app.database import Database


class SlugAlreadyExistsError(Exception):
    pass


class UrlNotFoundError(Exception):
    pass


class UrlService:
    def __init__(self, database: Database, base_url: str, slug_length: int = 7) -> None:
        self.database = database
        self.base_url = base_url.rstrip("/")
        self.slug_length = slug_length
        self.alphabet = string.ascii_letters + string.digits

    def create(self, target_url: str, custom_slug: str | None = None) -> dict:
        slug = custom_slug or self._generate_unique_slug()
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            exists = connection.execute("SELECT 1 FROM urls WHERE slug = ?", (slug,)).fetchone()
            if exists:
                raise SlugAlreadyExistsError(slug)
            connection.execute(
                "INSERT INTO urls(slug, target_url, created_at) VALUES (?, ?, ?)",
                (slug, target_url, now),
            )
        return self.get(slug)

    def get(self, slug: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM urls WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise UrlNotFoundError(slug)
        return self._row_to_dict(row)

    def resolve(self, slug: str) -> str:
        now = datetime.now(UTC).isoformat()
        with self.database.connect() as connection:
            row = connection.execute("SELECT target_url FROM urls WHERE slug = ?", (slug,)).fetchone()
            if row is None:
                raise UrlNotFoundError(slug)
            connection.execute(
                "UPDATE urls SET clicks = clicks + 1, last_accessed_at = ? WHERE slug = ?",
                (now, slug),
            )
            return str(row["target_url"])

    def _generate_unique_slug(self) -> str:
        for _ in range(20):
            slug = "".join(secrets.choice(self.alphabet) for _ in range(self.slug_length))
            with self.database.connect() as connection:
                exists = connection.execute("SELECT 1 FROM urls WHERE slug = ?", (slug,)).fetchone()
            if not exists:
                return slug
        raise RuntimeError("Failed to allocate unique slug after bounded retries")

    def _row_to_dict(self, row) -> dict:
        return {
            "slug": row["slug"],
            "short_url": f"{self.base_url}/{row['slug']}",
            "target_url": row["target_url"],
            "created_at": row["created_at"],
            "clicks": row["clicks"],
            "last_accessed_at": row["last_accessed_at"],
        }

