"""Group candidate articles that probably describe the same visit, and flag
groups that match visits already in data/visits.csv. Output is a review sheet;
nothing is merged into the public data automatically."""

import csv
import json
from datetime import date

from . import DATA_DIR

WINDOW_DAYS = 14


def _to_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        parts = value[:10].split("-")
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 15)
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def anchor_date(fields: dict, pub_date: str | None) -> date | None:
    return _to_date(fields.get("start_date")) or _to_date(pub_date)


def cluster_articles(items: list[dict], window_days: int = WINDOW_DAYS) -> list[list[dict]]:
    """items: dicts with keys url, title, pub_date, fields (rule extraction).
    Articles cluster when they share a visiting country and their anchor dates
    fall within `window_days` of the cluster's first article."""
    keyed = []
    for it in items:
        iso = it["fields"].get("visiting_country_iso3")
        d = anchor_date(it["fields"], it.get("pub_date"))
        keyed.append((iso or "", d or date.min, it))
    keyed.sort(key=lambda k: (k[0], k[1]))
    clusters: list[list[dict]] = []
    current, cur_iso, cur_date = [], None, None
    for iso, d, it in keyed:
        same = (iso and iso == cur_iso and d != date.min and cur_date not in (None, date.min)
                and abs((d - cur_date).days) <= window_days)
        if same:
            current.append(it)
        else:
            if current:
                clusters.append(current)
            current, cur_iso, cur_date = [it], iso, d
    if current:
        clusters.append(current)
    return clusters


def load_existing_visits(path=DATA_DIR / "visits.csv") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def match_existing(cluster: list[dict], visits: list[dict], window_days: int = 21) -> str:
    iso = cluster[0]["fields"].get("visiting_country_iso3")
    d = anchor_date(cluster[0]["fields"], cluster[0].get("pub_date"))
    if not iso or not d:
        return ""
    for v in visits:
        vd = _to_date(v["start_date"])
        if v["visiting_country_iso3"] == iso and vd and abs((vd - d).days) <= window_days:
            return v["visit_id"]
    return ""


def summarise(cluster: list[dict]) -> dict:
    f = [c["fields"] for c in cluster]
    starts = sorted(x["start_date"] for x in f if x.get("start_date"))
    ends = sorted(x["end_date"] for x in f if x.get("end_date"))
    union = lambda key: sorted({v for x in f for v in (x.get(key) or [])})
    return {
        "visiting_country_iso3": f[0].get("visiting_country_iso3") or "",
        "start_date": starts[0] if starts else "",
        "end_date": ends[-1] if ends else "",
        "delegation_size": next((x["delegation_size"] for x in f if x.get("delegation_size")), ""),
        "themes": ";".join(union("themes")),
        "hgs_mentioned": ";".join(union("hgs_mentioned")),
        "rwandan_hosts": ";".join(union("rwandan_hosts")),
        "rci_involvement": "explicit" if any(x.get("rci_involvement") == "explicit" for x in f) else "not_mentioned",
        "n_articles": len(cluster),
        "urls": " | ".join(c["url"] for c in cluster),
        "titles": " | ".join((c.get("title") or "")[:120] for c in cluster),
    }


def build_review_sheet(conn, out_path=DATA_DIR / "review" / "candidates.csv") -> int:
    rows = conn.execute(
        "SELECT a.id, a.url, a.title, a.pub_date, e.fields_json FROM articles a "
        "JOIN extractions e ON e.article_id = a.id AND e.method = 'rules' "
        "WHERE a.status = 'candidate'"
    ).fetchall()
    items = [{"id": r["id"], "url": r["url"], "title": r["title"], "pub_date": r["pub_date"],
              "fields": json.loads(r["fields_json"])} for r in rows]
    visits = load_existing_visits()
    clusters = cluster_articles(items)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["cluster", "existing_visit_id", "decision", "visiting_country_iso3", "start_date",
                  "end_date", "delegation_size", "themes", "hgs_mentioned", "rwandan_hosts",
                  "rci_involvement", "n_articles", "urls", "titles"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for i, cl in enumerate(clusters, start=1):
            row = summarise(cl)
            row.update(cluster=f"C{i:04d}", existing_visit_id=match_existing(cl, visits), decision="")
            w.writerow(row)
    return len(clusters)
