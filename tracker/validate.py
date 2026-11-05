"""Check data/visits.csv and data/sources.csv against config/vocab.yaml."""

import csv
import re
from pathlib import Path

import pycountry

from . import CONFIG_DIR, DATA_DIR, config

DATE_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
VISIT_COLUMNS = ("visit_id,start_date,end_date,date_precision,date_note,visiting_country_iso3,"
                 "visiting_country,visiting_entity,entity_type,delegation_size,lead,themes,"
                 "hgs_mentioned,rwandan_hosts,rci_involvement,co_facilitator,evidence,summary,"
                 "source_ids,notes,verified").split(",")
SOURCE_COLUMNS = "source_id,url,outlet,source_type,pub_date,title,language,accessed".split(",")
VERIFIED = {"snippet_only", "machine_read", "full_text_checked", "double_coded"}
MULTINATIONAL_OK = {"intergovernmental", "ngo", "think_tank_academic"}
ITINERARY_COLUMNS = ["visit_id", "date", "stop", "activity", "source_id"]
AU_REGIONS = {"North Africa", "East Africa", "Central Africa", "West Africa", "Southern Africa"}


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(";") if v.strip()]


def validate(data_dir: Path = DATA_DIR) -> list[str]:
    vocab = config.vocab()
    errors: list[str] = []

    with open(data_dir / "sources.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != SOURCE_COLUMNS:
            errors.append(f"sources.csv: columns must be {SOURCE_COLUMNS}")
        sources = list(reader)
    source_ids = set()
    for s in sources:
        sid = s["source_id"]
        if sid in source_ids:
            errors.append(f"{sid}: duplicate source_id")
        source_ids.add(sid)
        if not s["url"].startswith(("http://", "https://")):
            errors.append(f"{sid}: url must start with http(s)://")
        if s["source_type"] not in vocab["source_type"]:
            errors.append(f"{sid}: unknown source_type '{s['source_type']}'")
        if s["pub_date"] and not re.match(r"^\d{4}(-\d{2}){0,2}$", s["pub_date"]):
            errors.append(f"{sid}: pub_date '{s['pub_date']}' is not ISO")

    with open(data_dir / "visits.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != VISIT_COLUMNS:
            errors.append(f"visits.csv: columns must be {VISIT_COLUMNS}")
        visits = list(reader)
    used_sources = set()
    seen_ids = set()
    for v in visits:
        vid = v["visit_id"]
        if not re.match(r"^V\d{3,}$", vid):
            errors.append(f"{vid}: visit_id must look like V001")
        if vid in seen_ids:
            errors.append(f"{vid}: duplicate visit_id")
        seen_ids.add(vid)
        for col in ("start_date", "end_date"):
            if v[col] and not DATE_RE.match(v[col]):
                errors.append(f"{vid}: {col} '{v[col]}' is not YYYY-MM or YYYY-MM-DD")
        if v["start_date"] and v["end_date"] and v["end_date"] < v["start_date"]:
            errors.append(f"{vid}: end_date before start_date")
        if not v["start_date"]:
            errors.append(f"{vid}: start_date is required")
        if v["date_precision"] not in vocab["date_precision"]:
            errors.append(f"{vid}: unknown date_precision '{v['date_precision']}'")
        if v["date_precision"] != "day" and not v["date_note"]:
            errors.append(f"{vid}: date_note required when date_precision is not 'day'")
        iso = v["visiting_country_iso3"]
        if iso and not pycountry.countries.get(alpha_3=iso):
            errors.append(f"{vid}: unknown ISO3 code '{iso}'")
        if "(" in v["visiting_country"] or ";" in v["visiting_country"]:
            errors.append(f"{vid}: visiting_country should be a plain country name; put qualifiers in notes")
        if not iso and v["entity_type"] not in MULTINATIONAL_OK:
            errors.append(f"{vid}: visiting_country_iso3 required unless the delegation is a multinational body")
        if v["entity_type"] not in vocab["entity_type"]:
            errors.append(f"{vid}: unknown entity_type '{v['entity_type']}'")
        if not v["visiting_entity"].strip():
            errors.append(f"{vid}: visiting_entity is required (describe the delegation if the institution is not named)")
        if v["delegation_size"] and not v["delegation_size"].isdigit():
            errors.append(f"{vid}: delegation_size must be an integer")
        for t in _split(v["themes"]):
            if t not in vocab["themes"]:
                errors.append(f"{vid}: unknown theme '{t}'")
        if not _split(v["themes"]):
            errors.append(f"{vid}: at least one theme is required")
        for h in _split(v["hgs_mentioned"]):
            if h not in vocab["hgs"]:
                errors.append(f"{vid}: unknown HGS '{h}'")
        if v["rci_involvement"] not in vocab["rci_involvement"]:
            errors.append(f"{vid}: unknown rci_involvement '{v['rci_involvement']}'")
        if v["evidence"] not in vocab["evidence"]:
            errors.append(f"{vid}: unknown evidence '{v['evidence']}'")
        if v["verified"] not in VERIFIED:
            errors.append(f"{vid}: verified must be one of {sorted(VERIFIED)}")
        if not v["summary"]:
            errors.append(f"{vid}: summary is required")
        sids = _split(v["source_ids"])
        if not sids:
            errors.append(f"{vid}: at least one source is required")
        for sid in sids:
            used_sources.add(sid)
            if sid not in source_ids:
                errors.append(f"{vid}: source '{sid}' not found in sources.csv")

    itin_path = data_dir / "itinerary.csv"
    if itin_path.exists():
        with open(itin_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != ITINERARY_COLUMNS:
                errors.append(f"itinerary.csv: columns must be {ITINERARY_COLUMNS}")
            for i, row in enumerate(reader, start=2):
                where = f"itinerary.csv line {i}"
                if row["visit_id"] not in seen_ids:
                    errors.append(f"{where}: unknown visit_id '{row['visit_id']}'")
                if row["date"] and not re.match(r"^\d{4}-\d{2}-\d{2}$", row["date"]):
                    errors.append(f"{where}: date must be YYYY-MM-DD or blank")
                if not row["stop"]:
                    errors.append(f"{where}: stop is required")
                if row["activity"] not in vocab["itinerary_activity"]:
                    errors.append(f"{where}: unknown activity '{row['activity']}'")
                if row["source_id"] not in source_ids:
                    errors.append(f"{where}: source '{row['source_id']}' not found")
                used_sources.add(row["source_id"])

    for sid in sorted(source_ids - used_sources):
        errors.append(f"{sid}: source not used by any visit")
    errors.extend(validate_regions())
    return errors


def validate_regions(config_dir: Path = CONFIG_DIR) -> list[str]:
    """config/regions.csv must map valid ISO3 codes to the five AU regions, once each."""
    errors: list[str] = []
    seen: set[str] = set()
    with open(config_dir / "regions.csv", encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            iso, region = row["iso3"], row["region"]
            where = f"regions.csv line {i}"
            if iso in seen:
                errors.append(f"{where}: duplicate iso3 '{iso}'")
            seen.add(iso)
            if not pycountry.countries.get(alpha_3=iso):
                errors.append(f"{where}: unknown ISO3 code '{iso}'")
            if region not in AU_REGIONS:
                errors.append(f"{where}: region must be one of {sorted(AU_REGIONS)}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("visits.csv and sources.csv are valid.")
    return 0
