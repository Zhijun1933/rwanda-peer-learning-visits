from tracker import db, discover
from tracker.fetch import PoliteFetcher, blocked_by_policy

from .conftest import FakeResponse, FakeSession


def test_policy_blocks_rci_and_subdomains():
    dnc = ["rci.gov.rw", "cooperation.rw"]
    assert blocked_by_policy("https://www.rci.gov.rw/news", dnc)
    assert blocked_by_policy("https://cooperation.rw/x", dnc)
    assert not blocked_by_policy("https://www.newtimes.co.rw/article/1", dnc)
    assert not blocked_by_policy("https://notrci.gov.rw.example.com/", dnc)


def test_robots_disallow_is_respected(test_cfg):
    session = FakeSession({
        "https://site.example/robots.txt": FakeResponse(200, "User-agent: *\nDisallow: /private/\n"),
        "https://site.example/public/a": FakeResponse(200, "ok"),
    })
    f = PoliteFetcher(test_cfg, session=session)
    assert f.allowed("https://site.example/public/a")
    assert not f.allowed("https://site.example/private/b")
    assert f.get("https://site.example/private/b") is None
    assert "https://site.example/private/b" not in session.requested


def test_policy_block_never_touches_network(test_cfg):
    session = FakeSession({})
    f = PoliteFetcher(test_cfg, session=session)
    assert f.get("https://www.rci.gov.rw/anything") is None
    assert session.requested == []


def test_parse_sitemap_index_and_pages(fixtures):
    children, pages = discover.parse_sitemap((fixtures / "sitemap_index.xml").read_bytes())
    assert len(children) == 2 and pages == []
    children, pages = discover.parse_sitemap((fixtures / "sitemap_pages.xml").read_bytes())
    assert children == [] and len(pages) == 3


def test_walk_sitemaps_filters_by_slug_and_date(fixtures, test_cfg, tmp_path):
    session = FakeSession({
        "https://news.example.rw/robots.txt": FakeResponse(
            200, "User-agent: *\nAllow: /\nSitemap: https://news.example.rw/sitemap_index.xml\n"),
        "https://news.example.rw/sitemap_index.xml": FakeResponse(
            200, content=(fixtures / "sitemap_index.xml").read_bytes()),
        "https://news.example.rw/sitemap-2026-03.xml": FakeResponse(
            200, content=(fixtures / "sitemap_pages.xml").read_bytes()),
    })
    conn = db.connect(tmp_path / "t.db")
    f = PoliteFetcher(test_cfg, session=session)
    added = discover.walk_sitemaps(conn, f, "news.example.rw", test_cfg["slug_keywords"], since="2020-01-01")
    urls = [r["url"] for r in conn.execute("SELECT url FROM articles ORDER BY url")]
    assert added == 2
    assert urls == [
        "https://news.example.rw/article/101/news/malawian-officials-in-rwanda-for-study-tour",
        "https://news.example.rw/article/103/news/ghana-delegation-benchmarking-visit",
    ]
    # the 2014 child sitemap is skipped by the --since filter
    assert "https://news.example.rw/sitemap-2014-01.xml" not in session.requested


def test_gdelt_parsing_and_bad_payload(fixtures):
    arts = discover.parse_gdelt((fixtures / "gdelt.json").read_text())
    assert len(arts) == 2
    assert discover.parse_gdelt("Invalid query: phrase too short") == []


def test_gdelt_url_encodes_query():
    from datetime import datetime
    url = discover.gdelt_url('"study tour" Rwanda', datetime(2026, 1, 1), datetime(2026, 1, 8))
    assert "query=%22study%20tour%22%20Rwanda" in url
    assert "startdatetime=20260101000000" in url


def test_add_urls_dedupes(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    p = tmp_path / "urls.txt"
    p.write_text("# comment\nhttps://a.example/1\nhttps://a.example/1\nhttps://a.example/2\n")
    assert discover.add_urls_from_file(conn, str(p)) == 2


def test_gkg_sql_contains_since():
    sql = discover.gkg_sql("2018-01-01")
    assert "TIMESTAMP('2018-01-01')" in sql and "rwanda cooperation" in sql
