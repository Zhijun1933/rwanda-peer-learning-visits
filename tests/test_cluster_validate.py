import csv
import shutil

from tracker import DATA_DIR
from tracker.cluster import cluster_articles, match_existing, summarise
from tracker.validate import validate


def _item(url, iso, start=None, pub=None, hosts=()):
    return {"url": url, "title": url, "pub_date": pub,
            "fields": {"visiting_country_iso3": iso, "start_date": start, "end_date": None,
                       "rwandan_hosts": list(hosts), "themes": [], "hgs_mentioned": [],
                       "rci_involvement": "not_mentioned", "delegation_size": None}}


def test_cluster_groups_same_country_close_dates():
    items = [
        _item("a", "ZMB", "2025-09-28"),
        _item("b", "ZMB", None, pub="2025-10-01", hosts=["Ministry of Defence / RDF"]),
        _item("c", "ZMB", "2023-10-01"),
        _item("d", "NGA", "2025-09-29"),
    ]
    clusters = cluster_articles(items)
    groups = sorted(sorted(i["url"] for i in c) for c in clusters)
    assert groups == [["a", "b"], ["c"], ["d"]]


def test_summarise_unions_hosts():
    s = summarise([_item("a", "ZMB", "2025-09-28", hosts=["RALGA"]),
                   _item("b", "ZMB", None, hosts=["MINALOC", "RALGA"])])
    assert s["rwandan_hosts"] == "MINALOC;RALGA" and s["n_articles"] == 2


def test_match_existing_visit():
    visits = [{"visit_id": "V015", "visiting_country_iso3": "ZMB", "start_date": "2025-09-28"}]
    assert match_existing([_item("a", "ZMB", "2025-10-02")], visits) == "V015"
    assert match_existing([_item("a", "ZMB", "2024-10-02")], visits) == ""


def test_shipped_data_is_valid():
    assert validate() == []


def test_validator_catches_errors(tmp_path):
    shutil.copy(DATA_DIR / "sources.csv", tmp_path / "sources.csv")
    with open(DATA_DIR / "visits.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys())
    rows[0]["themes"] = "made_up_theme"
    rows[1]["visiting_country_iso3"] = "XXX"
    rows[2]["source_ids"] = "S999"
    with open(tmp_path / "visits.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    errors = " ".join(validate(tmp_path))
    assert "unknown theme 'made_up_theme'" in errors
    assert "unknown ISO3 code 'XXX'" in errors
    assert "source 'S999' not found" in errors
