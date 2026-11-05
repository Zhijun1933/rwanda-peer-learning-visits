"""Public exports that contain metadata and counts only, never article text.

  data/candidates.csv      candidate visits found by the crawler, awaiting review
  data/crawl_status.json   when the crawler last ran and what it found
  data/coding_summary.csv  number of coded segments per visit and analytic code
"""

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import DATA_DIR
from .cluster import build_review_sheet


def export_candidates(conn, data_dir: Path = DATA_DIR, new_urls: int | None = None) -> int:
    review = data_dir / "review" / "candidates.csv"
    n = build_review_sheet(conn, review)
    public = data_dir / "candidates.csv"
    with open(review, encoding="utf-8") as src, open(public, "w", newline="", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        fields = [f for f in reader.fieldnames if f != "decision"]
        w = csv.DictWriter(dst, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in reader:
            w.writerow(row)
    counts = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, COUNT(*) n FROM articles GROUP BY status")}
    status = {
        "last_run": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "candidate_groups": n,
        "new_urls_this_run": new_urls,
        "articles_by_status": counts,
    }
    (data_dir / "crawl_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return n


def coding_summary(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT COALESCE(av.visit_id, '') AS visit_id, s.code, COUNT(*) AS segments, "
        "COUNT(DISTINCT s.article_id) AS articles "
        "FROM segments s LEFT JOIN article_visit av ON av.article_id = s.article_id "
        "GROUP BY av.visit_id, s.code ORDER BY av.visit_id, s.code").fetchall()
    return [dict(r) for r in rows]


def export_coding(conn, data_dir: Path = DATA_DIR) -> int:
    rows = coding_summary(conn)
    with open(data_dir / "coding_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["visit_id", "code", "segments", "articles"])
        w.writeheader()
        w.writerows(rows)
    return len(rows)
