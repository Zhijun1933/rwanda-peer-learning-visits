"""Command-line interface: python -m tracker <command> --help"""

import argparse
import csv
import json
import sys
from pathlib import Path

from . import DATA_DIR, config, db, discover, extract
from .fetch import PoliteFetcher, blocked_by_policy

RELEVANCE_THRESHOLD = 0.5


def cmd_discover(args):
    conn = db.connect()
    if args.route == "sitemaps":
        n = discover.run_sitemaps(conn, since=args.since, domains=args.domain or None,
                                  max_sitemaps=args.max_sitemaps)
    elif args.route == "gdelt":
        cfg = config.sources()
        n = discover.run_gdelt(conn, PoliteFetcher(cfg), cfg["gdelt_queries"], days=args.days)
    conn.commit()
    print(f"{n} new URLs added.")


def cmd_gkg_sql(args):
    print(discover.gkg_sql(args.since, args.until))


def cmd_add_urls(args):
    conn = db.connect()
    n = discover.add_urls_from_file(conn, args.file, via=args.via)
    conn.commit()
    print(f"{n} new URLs added.")


def cmd_fetch(args):
    conn = db.connect()
    cfg = config.sources()
    fetcher = PoliteFetcher(cfg)
    rows = conn.execute("SELECT id, url, hint_title FROM articles WHERE status = 'new' "
                        "ORDER BY id LIMIT ?", (args.limit,)).fetchall()
    print(f"Fetching {len(rows)} articles (polite mode: >= {fetcher.min_delay}s per domain)...")
    counts = {}
    for r in rows:
        status, update = "error", {}
        try:
            if blocked_by_policy(r["url"], fetcher.do_not_crawl):
                status = "skipped_policy"
            elif not fetcher.allowed(r["url"]):
                status = "skipped_robots"
            else:
                resp = fetcher.get(r["url"], check_robots=False)
                update["http_status"] = resp.status_code
                if resp.status_code == 200:
                    rec = extract.html_to_record(resp.text, url=r["url"])
                    score = extract.relevance(rec["text"], rec["title"] or r["hint_title"] or "",
                                              cfg["visit_terms"])
                    update.update(title=rec["title"], pub_date=rec["date"], language=rec["language"],
                                  text=rec["text"], relevance=score)
                    status = "candidate" if score >= RELEVANCE_THRESHOLD else "irrelevant"
                else:
                    update["error"] = f"HTTP {resp.status_code}"
        except Exception as exc:  # keep going; record the problem
            update["error"] = str(exc)[:300]
        update.update(status=status, fetched_at=db.now())
        sets = ", ".join(f"{k} = ?" for k in update)
        conn.execute(f"UPDATE articles SET {sets} WHERE id = ?", (*update.values(), r["id"]))
        conn.commit()
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{status}] {r['url']}")
    print("Done:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "nothing to fetch")


def cmd_extract(args):
    conn = db.connect()
    rows = conn.execute(
        "SELECT a.id, a.title, a.text FROM articles a WHERE a.status = 'candidate' AND NOT EXISTS "
        "(SELECT 1 FROM extractions e WHERE e.article_id = a.id AND e.method = ?)",
        ("llm" if args.llm else "rules",)).fetchall()
    for r in rows:
        if args.llm:
            from .llm import extract_with_llm
            fields = extract_with_llm(r["text"] or "", r["title"] or "")
        else:
            fields = extract.extract_fields(r["text"] or "", r["title"] or "")
        conn.execute("INSERT OR REPLACE INTO extractions (article_id, method, created_at, fields_json) "
                     "VALUES (?, ?, ?, ?)",
                     (r["id"], "llm" if args.llm else "rules", db.now(), json.dumps(fields, ensure_ascii=False)))
        conn.commit()
    print(f"Extracted fields for {len(rows)} articles.")


def cmd_review(args):
    from .cluster import build_review_sheet
    conn = db.connect()
    out = DATA_DIR / "review" / "candidates.csv"
    n = build_review_sheet(conn, out)
    print(f"{n} candidate visit groups written to {out}")
    print("Fill the 'decision' column (new / merge:V### / reject), then add accepted rows to data/visits.csv.")


def cmd_export_texts(args):
    """Write candidate article texts as .txt files for ATLAS.ti / NVivo / Taguette."""
    conn = db.connect()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = conn.execute("SELECT id, url, title, pub_date, text FROM articles WHERE status = 'candidate'").fetchall()
    for r in rows:
        header = f"ID: A{r['id']:05d}\nURL: {r['url']}\nTITLE: {r['title']}\nDATE: {r['pub_date']}\n\n"
        (out / f"A{r['id']:05d}.txt").write_text(header + (r["text"] or ""), encoding="utf-8")
    print(f"{len(rows)} texts written to {out}/ (keep this folder private).")


def cmd_load_codes(args):
    conn = db.connect()
    with open(args.file, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        conn.execute("INSERT OR REPLACE INTO codes (code, name, parent, definition) VALUES (?, ?, ?, ?)",
                     (r["code"], r["name"], r.get("parent") or None, r.get("definition")))
    conn.commit()
    print(f"{len(rows)} codes loaded.")


def cmd_export_candidates(args):
    from .export import export_candidates
    n = export_candidates(db.connect(), new_urls=args.new_urls)
    print(f"{n} candidate groups written to data/candidates.csv")


def cmd_export_coding(args):
    from .export import export_coding
    n = export_coding(db.connect())
    print(f"{n} rows written to data/coding_summary.csv")


def cmd_status(args):
    conn = db.connect()
    for row in conn.execute("SELECT status, COUNT(*) n FROM articles GROUP BY status ORDER BY n DESC"):
        print(f"{row['status']:>16}  {row['n']}")
    for row in conn.execute("SELECT discovered_via, COUNT(*) n FROM articles GROUP BY discovered_via"):
        print(f"{'via ' + row['discovered_via']:>16}  {row['n']}")


def cmd_validate(args):
    from .validate import main
    sys.exit(main())


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tracker", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("discover", help="find candidate URLs")
    d.add_argument("route", choices=["sitemaps", "gdelt"])
    d.add_argument("--since", help="sitemaps: only URLs last modified on/after YYYY-MM-DD")
    d.add_argument("--domain", action="append", help="sitemaps: limit to this domain (repeatable)")
    d.add_argument("--days", type=int, default=90, help="gdelt: how many days back")
    d.add_argument("--max-sitemaps", type=int, default=500, help="sitemaps: cap on sitemap files per domain")
    d.set_defaults(func=cmd_discover)

    g = sub.add_parser("gkg-sql", help="print BigQuery SQL for historical discovery via GDELT GKG")
    g.add_argument("--since", default="2015-02-19")
    g.add_argument("--until", default="2100-01-01")
    g.set_defaults(func=cmd_gkg_sql)

    a = sub.add_parser("add-urls", help="add URLs from a text file or a CSV with a 'url' column")
    a.add_argument("file")
    a.add_argument("--via", default="manual", choices=["manual", "gkg"])
    a.set_defaults(func=cmd_add_urls)

    f = sub.add_parser("fetch", help="download new URLs politely and score relevance")
    f.add_argument("--limit", type=int, default=200)
    f.set_defaults(func=cmd_fetch)

    e = sub.add_parser("extract", help="pre-fill visit fields for candidate articles")
    e.add_argument("--llm", action="store_true", help="use the optional Claude-based extractor")
    e.set_defaults(func=cmd_extract)

    sub.add_parser("review", help="group candidates into likely visits for human review").set_defaults(func=cmd_review)

    x = sub.add_parser("export-texts", help="export candidate texts for qualitative coding software")
    x.add_argument("--out", default=str(DATA_DIR / "text"))
    x.set_defaults(func=cmd_export_texts)

    c = sub.add_parser("load-codes", help="load a code list (CSV: code,name,parent,definition)")
    c.add_argument("file")
    c.set_defaults(func=cmd_load_codes)

    ec = sub.add_parser("export-candidates", help="write public data/candidates.csv and crawl_status.json (no text)")
    ec.add_argument("--new-urls", type=int, default=None, help="number of URLs discovered this run, for the status file")
    ec.set_defaults(func=cmd_export_candidates)
    sub.add_parser("export-coding", help="write public data/coding_summary.csv (counts only)").set_defaults(func=cmd_export_coding)
    sub.add_parser("status", help="show pipeline counts").set_defaults(func=cmd_status)
    sub.add_parser("validate", help="check the public CSVs").set_defaults(func=cmd_validate)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
