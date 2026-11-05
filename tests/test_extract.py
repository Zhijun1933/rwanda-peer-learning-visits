from tracker import extract

VISIT_TERMS = ["study tour", "study visit", "benchmarking"]


def test_html_to_record_drops_boilerplate(fixtures):
    rec = extract.html_to_record((fixtures / "article.html").read_text(), url="https://news.example.rw/a")
    assert "Malawi" in rec["text"]
    assert "All rights reserved" not in rec["text"]
    assert rec["title"].startswith("Malawian district officials")


def test_relevance():
    assert extract.relevance("A delegation from Malawi is in Rwanda for a study tour.", "", VISIT_TERMS) >= 0.5
    assert extract.relevance("APR FC won the league in Kigali, Rwanda.", "", VISIT_TERMS) == 0.0
    assert extract.relevance("A study tour in Kenya.", "", VISIT_TERMS) == 0.0


def test_date_ranges():
    assert extract.date_range("from 28 September to 4 October 2025") == ("2025-09-28", "2025-10-04")
    assert extract.date_range("taking place from 1–6 June 2026") == ("2026-06-01", "2026-06-06")
    assert extract.date_range("from 23 - 29 June 2024, headed by") == ("2024-06-23", "2024-06-29")
    assert extract.date_range("in Rwanda from September 28 to October 4, 2025") == ("2025-09-28", "2025-10-04")
    assert extract.date_range("June 1-6, 2026") == ("2026-06-01", "2026-06-06")
    assert extract.date_range("from 27 December to 3 January 2026") == ("2025-12-27", "2026-01-03")
    assert extract.date_range("no dates here") == (None, None)


def test_delegation_size():
    assert extract.delegation_size("A delegation of 34 members will be visiting") == 34
    assert extract.delegation_size("a 15-member delegation") == 15
    assert extract.delegation_size("47 senior officers from Bangladesh") == 47
    assert extract.delegation_size("in 2026 the visit") is None


def test_countries_exclude_rwanda_and_use_demonyms():
    assert extract.likely_visiting_country("Rwandan officials hosted the team.", "Zambian officers on study tour") == "ZMB"
    assert extract.countries_mentioned("Students from Senegal, Morocco and Cote d'Ivoire visited Rwanda")[:3] == ["SEN", "MAR", "CIV"]
    assert "RWA" not in extract.countries_mentioned("Rwanda and Rwandan institutions")


def test_hosts_are_case_aware():
    hosts = extract.hosts_mentioned("They met the RGB and visited the Kigali Genocide Memorial.")
    assert hosts == ["Rwanda Governance Board", "Kigali Genocide Memorial"]
    # lower-case acronym inside a word or slug must not match
    assert extract.hosts_mentioned("the rdb-style rgbcolour") == []


def test_extract_fields_end_to_end(fixtures):
    rec = extract.html_to_record((fixtures / "article.html").read_text())
    f = extract.extract_fields(rec["text"], rec["title"])
    assert f["start_date"] == "2026-03-09" and f["end_date"] == "2026-03-14"
    assert f["visiting_country_iso3"] == "MWI"
    assert f["delegation_size"] == 18
    assert f["rci_involvement"] == "explicit"
    assert {"Imihigo", "Umuganda"} <= set(f["hgs_mentioned"])
    assert {"MINALOC", "Rwanda Governance Board", "RALGA"} <= set(f["rwandan_hosts"])
    assert "decentralization_local_govt" in f["themes"]
