# Learning from Rwanda: A Tracker of Peer-Learning Visits

A documented, source-linked dataset of delegations that travel to Rwanda to
learn from its institutions and programmes: study tours, study visits,
benchmarking visits and peer-learning missions. It comes with a small,
polite pipeline for finding and coding new reports.

**Interactive dashboard:** https://zhijun1933.github.io/rwanda-peer-learning-visits/

**Status:** seed release, November 2026. 26 visits by delegations from
19 countries and one intergovernmental body, 2018–2026, drawn from 40 public
sources. Three records have been checked against the full source text; the
rest are at `snippet_only` verification (see [Limitations](#limitations)).

## Background

Since the late 2000s, delegations from across Africa and beyond have come to
Rwanda to study programmes such as performance contracts (*Imihigo*),
community work (*Umuganda*), decentralised service delivery and digital
government. In 2018 Rwanda's Ministry of Foreign Affairs and International
Cooperation set up the Rwanda Cooperation Initiative (now Rwanda
Cooperation) to coordinate South-South exchange; study-visit requests from
partner governments are channelled through it
([Springer open-access chapter](https://link.springer.com/chapter/10.1007/978-3-031-55704-0_5)).
Many visits, especially by defence colleges, are also hosted directly by
Rwandan ministries and agencies.

No public, systematic record of these visits exists. This project assembles
one from published reports, so that patterns (who visits, when, to learn
what, from which institutions) can be described and studied.

## What's in the data

| File | Contents |
|---|---|
| [`data/visits.csv`](data/visits.csv) | One row per visit: dates, sending country and institution, delegation size, themes, Home-Grown Solutions named, Rwandan hosts, whether Rwanda Cooperation is mentioned, sources |
| [`data/sources.csv`](data/sources.csv) | One row per source: URL, outlet, type, publication date, headline |
| [`docs/codebook.md`](docs/codebook.md) | Definitions, inclusion rules and coding procedure |
| [`config/vocab.yaml`](config/vocab.yaml) | Controlled vocabularies used by the validator |
| [`index.html`](index.html) | The interactive dashboard (served by GitHub Pages; reads the two CSVs directly, so it updates whenever they change) |

The repository stores structured metadata, links and coder-written one-line
summaries only. **It does not redistribute article texts.**

## Running the pipeline

The pipeline runs on your own machine (Python 3.10+).

```bash
git clone https://github.com/Zhijun1933/rwanda-peer-learning-visits.git && cd rwanda-peer-learning-visits
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                                   # offline tests

# 1. Discover candidate URLs
python -m tracker discover sitemaps --since 2018-01-01   # Rwandan outlets and ministries
python -m tracker discover gdelt --days 90               # recent global news via GDELT
python -m tracker gkg-sql --since 2018-01-01 > gkg.sql   # historical: run in BigQuery,
python -m tracker add-urls gkg_results.csv --via gkg     #   then load the exported CSV
python -m tracker add-urls my_links.txt                  # links found by hand

# 2. Fetch politely, score relevance, pre-fill fields
python -m tracker fetch --limit 300
python -m tracker extract                 # rule-based suggestions
python -m tracker extract --llm           # optional: needs `pip install -e ".[llm]"` and ANTHROPIC_API_KEY

# 3. Review and code
python -m tracker review                  # writes data/review/candidates.csv
python -m tracker export-texts            # texts for ATLAS.ti / NVivo / Taguette (stays local)
python -m tracker status
python -m tracker validate                # run before every commit
```

Pipeline outputs (`data/tracker.db`, `data/raw/`, `data/text/`,
`data/review/`) are excluded from git.

## Crawling policy

- Every request checks `robots.txt` and honours `Crawl-delay`; the default
  minimum gap between requests to one domain is 5 seconds.
- A do-not-crawl list in `config/sources.yaml` is applied before any request.
  It includes Rwanda Cooperation's own websites and social media platforms.
- Discovery prefers sitemaps and news indexes over link-following.
- The user agent identifies the project as academic research.
- Article texts are cached locally for coding and are never published.

## Limitations

- **Reporting bias.** The Ministry of Defence publishes study tours
  systematically, so defence-college visits (13 of 26 seed records) are
  over-represented relative to civilian visits, which are reported unevenly.
- **"Not mentioned" is not "absent".** `rci_involvement = not_mentioned`
  only means no source names Rwanda Cooperation.
- **Language.** Seed sources are in English. French and Kinyarwanda coverage
  is a priority for the next release.
- **Verification.** Seed records were coded from search-result text and
  linked pages on 2026-11-04; most are marked `snippet_only`. Rows are upgraded
  to `full_text_checked` as each source is read in full. Known discrepancies
  between sources are recorded in the `notes` column.

## Contributing

Corrections and additional sources are welcome through issues or pull
requests. Please cite a public source for every change and run
`python -m tracker validate`.

## Citation

He, Zhijun. 2026. *Learning from Rwanda: A Tracker of Peer-Learning Visits*
(version 0.1). GitHub repository.

## License

Code: MIT (see `LICENSE`). Data (`data/*.csv`, `docs/`): CC BY 4.0 (see
`data/LICENSE-DATA.md`). Linked articles remain the property of their
publishers.
