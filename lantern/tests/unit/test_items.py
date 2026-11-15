from datetime import UTC, datetime

from lantern.items import Item, excerpt, normalize_url, parse_date, strip_html


def test_normalize_url_ignores_noise():
    assert normalize_url("https://www.Example.com/a/?utm_source=x&id=2#top") == "example.com/a?id=2"
    assert normalize_url("http://example.com/a") == normalize_url("https://example.com/a/")


def test_parse_date_formats_are_utc():
    assert parse_date("2026-10-23T10:00:00+02:00") == datetime(2026, 10, 23, 8, tzinfo=UTC)
    assert parse_date("Fri, 23 Oct 2026 09:00:00 GMT") == datetime(2026, 10, 23, 9, tzinfo=UTC)
    assert parse_date("Oct 23, 2026") == datetime(2026, 10, 23, tzinfo=UTC)
    assert parse_date("October 23, 2026") == datetime(2026, 10, 23, tzinfo=UTC)
    assert parse_date("soon") is None and parse_date(None) is None


def test_reading_minutes_only_with_a_body():
    assert Item("u", "t", "s", words=100).reading_minutes is None
    assert Item("u", "t", "s", words=460).reading_minutes == 2
    assert Item("u", "t", "s").reading_minutes is None


def test_text_helpers():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert excerpt("word " * 100, 20).endswith("…")
    assert excerpt("short") == "short"
