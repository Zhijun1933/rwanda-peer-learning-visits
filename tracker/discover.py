"""Find candidate article URLs.

Four routes, all of which respect robots.txt and the do-not-crawl list:
  * sitemaps  - walk the sitemaps of Rwandan outlets and ministries, keeping
                URLs whose slug matches study-visit keywords (covers archives)
  * gdelt     - GDELT DOC 2.0 API keyword search (about the last 3 months)
  * gkg       - print a BigQuery SQL query over the GDELT GKG for the full
                history since 2015; export results to CSV and load with add-urls
  * manual    - a CSV or text file of URLs found by hand
"""

import csv
import gzip
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlsplit

from . import config, db
from .fetch import PoliteFetcher, blocked_by_policy

SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


# ---------------------------------------------------------------- sitemaps
def parse_sitemap(xml_bytes: bytes) -> tuple[list[tuple[str, str | None]], list[tuple[str, str | None]]]:
    """Return (child_sitemaps, page_urls); each item is (loc, lastmod)."""
    if xml_bytes[:2] == b"\x1f\x8b":
        xml_bytes = gzip.decompress(xml_bytes)
    root = ET.fromstring(xml_bytes)
    tag = root.tag.replace(SM_NS, "")
    items = []
    for node in root:
        loc = node.findtext(f"{SM_NS}loc") or node.findtext("loc")
        lastmod = node.findtext(f"{SM_NS}lastmod") or node.findtext("lastmod")
        if loc:
            items.append((loc.strip(), lastmod.strip() if lastmod else None))
    return (items, []) if tag == "sitemapindex" else ([], items)


def slug_matches(url: str, keywords: list[str]) -> bool:
    path = urlsplit(url).path.lower()
    return any(k in path for k in keywords)


def _lastmod_ok(lastmod: str | None, since: str | None) -> bool:
    return not since or not lastmod or lastmod[:10] >= since


def walk_sitemaps(conn, fetcher: PoliteFetcher, domain: str, keywords: list[str],
                  since: str | None = None, max_sitemaps: int = 500) -> int:
    base = f"https://{domain}"
    queue = [(s, None) for s in fetcher.sitemaps(base)] or [(base + "/sitemap.xml", None)]
    seen, added, visited = set(), 0, 0
    while queue and visited < max_sitemaps:
        sm_url, lastmod = queue.pop(0)
        if sm_url in seen or not _lastmod_ok(lastmod, since):
            continue
        seen.add(sm_url)
        visited += 1
        try:
            resp = fetcher.get(sm_url)
        except Exception as exc:  # network errors are logged and skipped
            print(f"  ! {sm_url}: {exc}")
            continue
        if resp is None or resp.status_code != 200:
            continue
        try:
            children, pages = parse_sitemap(resp.content)
        except ET.ParseError:
            continue
        queue.extend(children)
        for loc, page_lastmod in pages:
            if slug_matches(loc, keywords) and _lastmod_ok(page_lastmod, since):
                added += db.add_article(conn, loc, "sitemap")
    return added


# ------------------------------------------------------------------- GDELT
GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"


def gdelt_url(query: str, start: datetime, end: datetime, maxrecords: int = 250) -> str:
    return (f"{GDELT_DOC}?query={quote(query)}&mode=artlist&format=json"
            f"&maxrecords={maxrecords}&sort=datedesc"
            f"&startdatetime={start:%Y%m%d%H%M%S}&enddatetime={end:%Y%m%d%H%M%S}")


def parse_gdelt(payload: str) -> list[dict]:
    """GDELT returns plain-text errors on bad queries; treat those as empty."""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    return data.get("articles", []) or []


def run_gdelt(conn, fetcher: PoliteFetcher, queries: list[str], days: int = 90,
              window_days: int = 7) -> int:
    end = datetime.now(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(days=days)
    added = 0
    for q in queries:
        w_start = start
        while w_start < end:
            w_end = min(w_start + timedelta(days=window_days), end)
            resp = fetcher.get(gdelt_url(q, w_start, w_end), check_robots=False)
            if resp is not None and resp.status_code == 200:
                for art in parse_gdelt(resp.text):
                    url = art.get("url")
                    if url and not blocked_by_policy(url, fetcher.do_not_crawl):
                        added += db.add_article(conn, url, "gdelt", art.get("title"))
            w_start = w_end
    return added


# --------------------------------------------------------------- GDELT GKG
GKG_SQL = """-- Run in the Google BigQuery console (the free sandbox allows 1 TB of scanning a month).
-- Before running, check the bytes estimate shown in the console; if it is too large,
-- narrow the date range and run one year at a time.
-- Export the result as CSV, then: python -m tracker add-urls results.csv --via gkg
SELECT DISTINCT
  DocumentIdentifier AS url,
  SourceCommonName   AS outlet,
  PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS seen_date
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME >= TIMESTAMP('{since}')
  AND _PARTITIONTIME <  TIMESTAMP('{until}')
  AND SourceCollectionIdentifier = 1            -- web news
  AND (
        LOWER(V2Organizations) LIKE '%rwanda cooperation%'
     OR (
          REGEXP_CONTAINS(LOWER(DocumentIdentifier),
              r'study-tour|study-visit|studytour|benchmark|learning-visit|exposure-visit|peer-learning|learn-from-rwanda')
          AND (REGEXP_CONTAINS(LOWER(DocumentIdentifier), r'rwanda|kigali')
               OR ENDS_WITH(LOWER(SourceCommonName), '.rw'))
        )
  )
ORDER BY seen_date
"""


def gkg_sql(since: str = "2015-02-19", until: str = "2100-01-01") -> str:
    return GKG_SQL.format(since=since, until=until)


# ------------------------------------------------------------------ manual
def add_urls_from_file(conn, path: str, via: str = "manual") -> int:
    """Accept a plain list of URLs or a CSV with a `url` column."""
    added = 0
    with open(path, encoding="utf-8") as f:
        first = f.readline()
        f.seek(0)
        if "url" in first.lower().split(","):
            for row in csv.DictReader(f):
                if row.get("url"):
                    added += db.add_article(conn, row["url"], via, row.get("title"))
        else:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    added += db.add_article(conn, line, via)
    return added


def run_sitemaps(conn, since: str | None = None, domains: list[str] | None = None,
                 max_sitemaps: int = 500) -> int:
    cfg = config.sources()
    fetcher = PoliteFetcher(cfg)
    total = 0
    for domain in domains or cfg["sitemap_domains"]:
        print(f"- sitemaps: {domain}")
        n = walk_sitemaps(conn, fetcher, domain, cfg["slug_keywords"], since=since,
                          max_sitemaps=max_sitemaps)
        conn.commit()
        print(f"  {n} new candidate URLs")
        total += n
    return total
