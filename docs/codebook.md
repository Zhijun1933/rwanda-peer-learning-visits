# Codebook

This codebook defines every field in `data/visits.csv` and `data/sources.csv`.
Controlled values live in `config/vocab.yaml`; `python -m tracker validate`
checks both files against it.

## Unit of observation

One row in `visits.csv` is **one delegation's visit to Rwanda**, in which a
delegation from another country, a subnational government or an organisation
comes to learn from Rwandan institutions or programmes. Called a study visit,
study tour, benchmarking visit, learning visit, exposure visit or
peer-learning mission.

**Include:** the delegation's stated purpose is learning or experience-sharing,
and at least one source documents the visit.

**Exclude:** state visits and bilateral negotiations with no learning component;
conferences and summits hosted in Rwanda (unless a separate study tour is
documented); Rwandan delegations travelling abroad; tourism and private trips.

**One visit, many sources.** Several articles often cover the same visit (one per
host institution). Merge them into one row and list every source in
`source_ids`. Treat two delegations from the same country as separate visits
when their dates do not overlap or their institutions differ.

## visits.csv

| Field | Definition | Rules |
|---|---|---|
| `visit_id` | Stable identifier `V###` | Never reused, even if a row is deleted |
| `start_date`, `end_date` | ISO dates (`YYYY-MM-DD`, or `YYYY-MM` when only the month is known) | Leave `end_date` blank if unknown |
| `date_precision` | `day`, `month` or `approx` | `approx` when dates are inferred from a single meeting or a report date |
| `date_note` | Free text explaining how dates were derived | Required when `date_precision` is not `day` |
| `visiting_country_iso3` | ISO 3166-1 alpha-3 code of the sending country | Blank only for multinational bodies (intergovernmental, continental associations) |
| `visiting_country` | Plain country name (current name of the sending state) | No qualifiers; put historical names or co-participants in `notes`. Blank for multinational bodies. Region is derived from the ISO3 code (see below), not coded separately |
| `visiting_entity` | Institution(s) the delegation came from, as named in the sources | |
| `entity_type` | Type of sending institution | Controlled vocabulary |
| `delegation_size` | Number of delegates, if stated | Integer only. Explain partial counts in `notes` |
| `lead` | Head of delegation and title, as reported | |
| `themes` | Policy areas the visit focused on | Controlled vocabulary, `;`-separated. Code only what sources state |
| `hgs_mentioned` | Home-Grown Solutions named in the sources | Controlled vocabulary. Named explicitly, not inferred |
| `rwandan_hosts` | Rwandan institutions the delegation met or visited | Use the short names listed below |
| `rci_involvement` | `explicit` if any source names Rwanda Cooperation / RCI | `not_mentioned` is not evidence that RCI was absent |
| `co_facilitator` | Third parties that organised or funded the visit | e.g. UNDP, g7+, World Bank |
| `evidence` | Strongest evidence type available | `report` > `social_post` > `programme` |
| `summary` | One sentence written by the coder | Original wording only; never copy from a source |
| `source_ids` | Links to `sources.csv` | `;`-separated |
| `notes` | Discrepancies between sources, coding decisions | |
| `verified` | `snippet_only` (coded from search-result text), `machine_read` (source pages opened and fields extracted by an automated reader), `full_text_checked` (a person read every source), `double_coded` | Upgrade as checks are done |

### Short names for Rwandan hosts

Use these forms so hosts can be counted: `Rwanda Cooperation`,
`Rwanda Governance Board`, `Rwanda Development Board`, `Rwanda Revenue Authority`,
`MINALOC`, `MINECOFIN`, `MIFOTRA`, `MINIJUST`, `MININTER`, `MINUBUMWE`,
`MINEDUC`, `Ministry of Health`, `Ministry of Defence / RDF`,
`Office of the Auditor General`, `Office of the Ombudsman`,
`National Bank of Rwanda`, `RALGA`, `City of Kigali`, `Parliament of Rwanda`,
`Office of the Prime Minister`, `Kigali Genocide Memorial`,
`Rwanda Peace Academy`, and districts as `<Name> District`.

## itinerary.csv

One row per stop on a visit's programme, recorded only when a source names the
stop. Used to study which institutions and sites recur across delegations.

| Field | Definition |
|---|---|
| `visit_id` | Links to `visits.csv` |
| `date` | `YYYY-MM-DD` if the source dates the stop, else blank |
| `stop` | Institution or site, using the short host names above where possible |
| `activity` | `briefing`, `site_visit`, `memorial`, `courtesy_call`, `field_visit`, `other` |
| `source_id` | The source that names the stop |

## sources.csv

| Field | Definition |
|---|---|
| `source_id` | Stable identifier `S###` |
| `url` | Canonical URL |
| `outlet` | Publisher name |
| `source_type` | Controlled vocabulary (Rwandan media, Rwandan government, visiting-country media, and others) |
| `pub_date` | Publication date, as precise as known |
| `title` | Headline as published |
| `language` | ISO 639-1 code |
| `accessed` | Date the coder last opened the source |

Full article texts are **not** stored in this repository. The crawler caches
them locally under `data/raw/` and `data/text/`, which `.gitignore` excludes.

## Coding procedure

1. The pipeline proposes candidate articles and pre-fills fields
   (`python -m tracker extract`). Pre-filled values are suggestions only.
2. A coder reads the full text and accepts, corrects or rejects each candidate.
3. Accepted candidates are merged into visits (`python -m tracker cluster` groups
   likely duplicates for review).
4. Set `verified` to `full_text_checked` once the coder has read every source
   for the row. A sample of rows is double-coded by a second coder to report
   agreement.
5. Run `python -m tracker validate` before every commit.

## Regions

Sending regions are derived from `visiting_country_iso3` using
[`config/regions.csv`](../config/regions.csv), which follows the African
Union's five regions (North, East, Central, West and Southern Africa).
Burundi is therefore in Central Africa and Sudan and South Sudan in East
Africa, whatever their other memberships (EAC, SADC, IGAD). Countries outside
the continent are grouped as "Outside Africa", and records with a blank ISO3
code (multinational bodies) as "Multinational".
