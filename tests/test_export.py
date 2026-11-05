import csv
import json

from tracker import db, extract
from tracker.export import coding_summary, export_candidates


def _seed(conn, fixtures):
    db.add_article(conn, "https://news.example.rw/a", "manual")
    rec = extract.html_to_record((fixtures / "article.html").read_text())
    conn.execute("UPDATE articles SET status='candidate', title=?, text=?, pub_date=? WHERE url=?",
                 (rec["title"], rec["text"], rec["date"], "https://news.example.rw/a"))
    fields = extract.extract_fields(rec["text"], rec["title"])
    conn.execute("INSERT INTO extractions (article_id, method, created_at, fields_json) VALUES (1, 'rules', ?, ?)",
                 (db.now(), json.dumps(fields)))
    conn.commit()


def test_export_candidates_has_no_text(tmp_path, fixtures):
    conn = db.connect(tmp_path / "t.db")
    _seed(conn, fixtures)
    n = export_candidates(conn, data_dir=tmp_path, new_urls=1)
    assert n == 1
    rows = list(csv.DictReader(open(tmp_path / "candidates.csv", encoding="utf-8")))
    assert rows[0]["visiting_country_iso3"] == "MWI"
    assert "decision" not in rows[0]
    blob = (tmp_path / "candidates.csv").read_text()
    assert "monthly community work day" not in blob  # article body never exported
    status = json.loads((tmp_path / "crawl_status.json").read_text())
    assert status["candidate_groups"] == 1 and status["new_urls_this_run"] == 1


def test_coding_summary_counts(tmp_path, fixtures):
    conn = db.connect(tmp_path / "t.db")
    _seed(conn, fixtures)
    conn.execute("INSERT INTO codes (code, name) VALUES ('A1', 'Model claim'), ('B1', 'Emulation intent')")
    conn.execute("INSERT INTO article_visit (article_id, visit_id) VALUES (1, 'V099')")
    for code in ("A1", "A1", "B1"):
        conn.execute("INSERT INTO segments (article_id, code, start_char, end_char, created_at) VALUES (1, ?, 0, 10, ?)",
                     (code, db.now()))
    rows = coding_summary(conn)
    assert rows == [{"visit_id": "V099", "code": "A1", "segments": 2, "articles": 1},
                    {"visit_id": "V099", "code": "B1", "segments": 1, "articles": 1}]
