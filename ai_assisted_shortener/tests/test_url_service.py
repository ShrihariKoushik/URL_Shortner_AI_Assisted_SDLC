from datetime import UTC, datetime, timedelta

import pytest

from app.database import Database
from app.url_service import LinkClickLimitExceededError, LinkExpiredError, UrlService


def make_service(tmp_path):
    return UrlService(Database(tmp_path / "links.db"), "http://test/r")


def test_create_resolve_and_stats(tmp_path):
    service = make_service(tmp_path)
    link = service.create("https://example.com", custom_endpoint="abc")

    assert link.code == "abc"
    assert link.clicks == 0
    assert service.resolve("abc") == "https://example.com"

    stats = service.get("abc")
    assert stats.clicks == 1
    assert stats.last_outcome == "resolved"


def test_expired_link_is_blocked_and_not_counted(tmp_path):
    service = make_service(tmp_path)
    service.create("https://example.com", custom_endpoint="old", expires_at=datetime.now(UTC) - timedelta(days=1))

    with pytest.raises(LinkExpiredError):
        service.resolve("old")

    stats = service.get("old")
    assert stats.clicks == 0
    assert stats.last_outcome == "expired"


def test_max_click_limit_blocks_after_limit(tmp_path):
    service = make_service(tmp_path)
    service.create("https://example.com", custom_endpoint="once", max_clicks=1)

    assert service.resolve("once") == "https://example.com"
    with pytest.raises(LinkClickLimitExceededError):
        service.resolve("once")

    stats = service.get("once")
    assert stats.clicks == 1
    assert stats.last_outcome == "click_limit_exceeded"
