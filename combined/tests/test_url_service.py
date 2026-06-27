from app.database import Database
from app.url_service import SlugAlreadyExistsError, UrlService


def test_create_resolve_and_stats(tmp_path):
    service = UrlService(Database(f"sqlite:///{tmp_path / 'app.db'}"), "http://testserver")

    created = service.create("https://example.com/path", custom_slug="demo")
    assert created["short_url"] == "http://testserver/demo"
    assert created["clicks"] == 0

    assert service.resolve("demo") == "https://example.com/path"
    stats = service.get("demo")
    assert stats["clicks"] == 1
    assert stats["last_accessed_at"] is not None


def test_duplicate_custom_slug_is_rejected(tmp_path):
    service = UrlService(Database(f"sqlite:///{tmp_path / 'app.db'}"), "http://testserver")
    service.create("https://example.com", custom_slug="same")

    try:
        service.create("https://example.org", custom_slug="same")
    except SlugAlreadyExistsError:
        pass
    else:
        raise AssertionError("expected duplicate slug rejection")

