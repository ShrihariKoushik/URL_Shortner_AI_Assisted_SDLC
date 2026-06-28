import secrets
import string
from datetime import UTC, datetime
from sqlite3 import IntegrityError

from app.database import Database
from app.schemas import LinkResponse, LinkStatsResponse


class LinkError(Exception):
    pass


class LinkNotFoundError(LinkError):
    pass


class LinkAlreadyExistsError(LinkError):
    pass


class LinkExpiredError(LinkError):
    pass


class LinkDisabledError(LinkError):
    pass


class LinkClickLimitExceededError(LinkError):
    pass


class UrlService:
    def __init__(self, database: Database, public_base_url: str, code_length: int = 7) -> None:
        self.database = database
        self.public_base_url = public_base_url.rstrip("/")
        self.code_length = code_length

    def create(
        self,
        target_url: str,
        custom_endpoint: str | None = None,
        expires_at: datetime | None = None,
        max_clicks: int | None = None,
    ) -> LinkResponse:
        code = custom_endpoint or self._generate_code()
        now = datetime.now(UTC).isoformat()
        expires_value = expires_at.isoformat() if expires_at else None
        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO links (code, target_url, created_at, expires_at, max_clicks)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (code, target_url, now, expires_value, max_clicks),
                )
        except IntegrityError as exc:
            raise LinkAlreadyExistsError(code) from exc
        return self.get(code)

    def resolve(self, code: str, user_agent: str | None = None, referrer: str | None = None) -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
            if row is None:
                raise LinkNotFoundError(code)
            outcome = self._resolve_outcome(row)
            self._record_click_event(connection, code, user_agent, referrer, outcome)
            if outcome != "resolved":
                connection.commit()
            if outcome == "disabled":
                raise LinkDisabledError(code)
            if outcome == "expired":
                raise LinkExpiredError(code)
            if outcome == "click_limit_exceeded":
                raise LinkClickLimitExceededError(code)
            connection.execute("UPDATE links SET clicks = clicks + 1 WHERE code = ?", (code,))
            return str(row["target_url"])

    def get(self, code: str) -> LinkStatsResponse:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM links WHERE code = ?", (code,)).fetchone()
            if row is None:
                raise LinkNotFoundError(code)
            event = connection.execute(
                "SELECT occurred_at, outcome FROM click_events WHERE code = ? ORDER BY id DESC LIMIT 1",
                (code,),
            ).fetchone()
        base = self._to_response(row).model_dump()
        base["last_accessed_at"] = datetime.fromisoformat(event["occurred_at"]) if event else None
        base["last_outcome"] = event["outcome"] if event else None
        return LinkStatsResponse(**base)

    def disable(self, code: str) -> LinkStatsResponse:
        with self.database.connect() as connection:
            cursor = connection.execute("UPDATE links SET disabled = 1 WHERE code = ?", (code,))
            if cursor.rowcount == 0:
                raise LinkNotFoundError(code)
        return self.get(code)

    def _resolve_outcome(self, row) -> str:
        if bool(row["disabled"]):
            return "disabled"
        expires_at = row["expires_at"]
        if expires_at and datetime.now(UTC) >= datetime.fromisoformat(expires_at):
            return "expired"
        max_clicks = row["max_clicks"]
        if max_clicks is not None and int(row["clicks"]) >= int(max_clicks):
            return "click_limit_exceeded"
        return "resolved"

    def _record_click_event(self, connection, code: str, user_agent: str | None, referrer: str | None, outcome: str) -> None:
        connection.execute(
            """
            INSERT INTO click_events (code, occurred_at, user_agent, referrer, outcome)
            VALUES (?, ?, ?, ?, ?)
            """,
            (code, datetime.now(UTC).isoformat(), user_agent, referrer, outcome),
        )

    def _generate_code(self) -> str:
        alphabet = string.ascii_letters + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(self.code_length))
            with self.database.connect() as connection:
                exists = connection.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone()
            if not exists:
                return code
        raise RuntimeError("could not allocate unique short code")

    def _to_response(self, row) -> LinkResponse:
        return LinkResponse(
            code=row["code"],
            short_url=f"{self.public_base_url}/{row['code']}",
            target_url=row["target_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            max_clicks=row["max_clicks"],
            clicks=row["clicks"],
            disabled=bool(row["disabled"]),
        )

