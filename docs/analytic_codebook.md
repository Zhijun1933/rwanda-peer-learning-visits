# Analytic codebook

For qualitative coding of the full texts cached locally by the crawler.
Research question: how does hosting delegations from African states that come
to study Rwanda as a development model shape how Rwandan officials claim
sovereignty for their post-conflict state, at home and abroad?

Code segments in the local `tracker.db` (`segments` table) or export the texts to
ATLAS.ti / NVivo / Taguette. Only aggregate counts are published
(`python -m tracker export-coding` writes `data/coding_summary.csv`); coded
quotations stay local. Each code has a definition, an inclusion rule and
an exclusion rule. Refine inductively; log every change with its date.

## Analytic dimensions (added 2026-11-05)

A sharper working question (from V. Waweru, 5 Nov 2026): *how does Rwanda
use study visits to project an image of **sovereign policy autonomy** and to
establish its **status as a development leader** among African states?*
The two halves are different claims made to different reference groups:
autonomy is measured against donors, status against African peers. Each code
is assigned one dimension (`dimension` column in
[`config/analytic_codes.csv`](../config/analytic_codes.csv)) so that coded
passages can be read against that question, including the evidence that
cuts against it.

| Dimension | Codes | What it captures |
|---|---|---|
| `autonomy` | A3, A4, D4 | Rwanda as author of its own policy, independent of donors |
| `autonomy_limits` | C5 | Evidence that cuts against autonomy: donors or IOs organise or pay for the visit |
| `status` | A1, B1, B2, B4, D1, D3 | Rwanda as model, leader or norm source, claimed by hosts or granted by guests |
| `status_limits` | B3, B5 | Guests who borrow selectively or frame the visit as mutual, not deferential |
| `legitimation` | A2, A5, A6 | Narratives that ground both claims (genocide-to-transformation, unity, security) |
| `apparatus` | C1–C4, D2 | How the exhibition is staged and tied to diplomacy |

The `_limits` dimensions are there on purpose: a reading that only counts
confirming passages cannot test the question.

## A. How Rwanda presents itself (host voice)

| Code | Definition | Include | Exclude |
|---|---|---|---|
| A1 Model claim | Rwanda described as a model, example or reference point | "Rwanda is a shining example", "learn from Rwanda's model" | Generic praise with no comparative claim |
| A2 Catastrophe-to-transformation narrative | The visit is framed by the 1994 genocide and recovery since | Memorial visits framed as the start of the story; "a nation transformed" | Factual mention of the memorial with no narrative link |
| A3 Home-grown authorship | Solutions presented as Rwandan-made, not imported | "home-grown", "our own solutions", HGS named as Rwandan innovation | HGS named only as programme labels |
| A4 Ownership and self-reliance | Emphasis on self-determination, not depending on donors | "we decided ourselves", "dignity", "not waiting for aid" | |
| A5 Unity and identity | National unity, Ndi Umunyarwanda, Itorero as the base of development | | |
| A6 Security as a precondition | Security and the RDF presented as the foundation of development | Especially in military study tours | |

## B. How visitors frame Rwanda (guest voice)

| Code | Definition |
|---|---|
| B1 Emulation intent | The visitor says they will adopt or adapt a programme |
| B2 Similarity claim | The visitor stresses shared conditions (post-conflict, resource curse, decentralisation) |
| B3 Selective borrowing | The visitor picks specific tools while distancing from the whole model |
| B4 Status deference | The visitor positions Rwanda as senior, leading or exemplary |
| B5 Reciprocity | The visitor frames the visit as mutual learning or offers something back |

## C. Exhibition apparatus

| Code | Definition |
|---|---|
| C1 Itinerary standardisation | The same sites and briefings recur across delegations (memorial, RGB, RDB, a model village, a district) |
| C2 Showcase sites | Specific places used as demonstrations (Karama, Mbyo, Nyandungu, Irembo, Kigali car-free zone) |
| C3 Gatekeeping | RCI or a ministry decides what visitors see, who briefs them, what is off-limits |
| C4 Monetisation | Fees, cost-sharing, RCI described as a company or service provider |
| C5 Third-party sponsorship | Donors or IOs (UNDP, g7+, World Bank, UN-Habitat, Gavi) organising or paying |

## D. Sovereignty claims

| Code | Definition |
|---|---|
| D1 Domestic audience | The visit reported to Rwandans as international recognition |
| D2 Foreign-policy instrument | Visits tied to bilateral agreements, MoUs, joint commissions or South-South diplomacy |
| D3 Norm entrepreneurship | Rwanda presenting itself as a source of governance norms for Africa |
| D4 Counter-narrative | Explicit or implicit rebuttal of external criticism (donors, human rights reports) |

## Memo prompts

- Which institutions appear in almost every itinerary, and which only appear for certain visitors?
- How do military study tours differ in narrative from civilian ones?
- Are there visits where Rwandan coverage and visiting-country coverage frame the same visit differently?
- When does the genocide narrative appear, and when is it absent?

## Change log

### 2026-11-05 — dimensions added; pilot round 1 (machine-coded)

Added the `dimension` column and the section above. Ran a first pilot on a
seeded stratified sample of 26 sources (24 readable), coded by machine
against this codebook; 114 coded passages, 136 code applications, 34% low
confidence. Not yet checked by a human coder, so its counts are not
published in `data/coding_summary.csv`. Full write-up:
[`docs/pilots/2026-11-pilot1.md`](pilots/2026-11-pilot1.md).

Revisions proposed by the pilot, **pending human review** (definitions above
are unchanged until reviewed):

1. **Code content, record voice separately.** A2, A5, A6 (host only) and B2,
   B5 (guest only) failed when the other side said the same thing; hosts
   calling a visit an "exchange of experiences" had no code at all. Proposal:
   make these codes voice-neutral and analyse speaker (host, guest, narrator,
   third party) as an attribute. A1 and B4 would then become one code,
   "model or leader claim", split by speaker at analysis time.
2. **New code, legitimation: leadership or political will as the
   explanation** for Rwanda's results (host and guest alike, 3+ sources).
3. **New code, status_limits: one destination among several** (the
   delegation also visits other countries or names other models). Fold the
   rarely usable B3 into it.
4. **C1 becomes a cross-source measure** computed from `data/itinerary.csv`,
   not a passage code. **C2 becomes an open list** (Umwalimu SACCO, Isange One
   Stop Centre, RDF headquarters and welfare institutions came up).
5. **Tighten thresholds.** D2 only when an agreement, MoU or joint commission
   is named; generic "strengthening cooperation" is not coded. B4 gets an
   exclusion rule for generic praise. D1 only when the text frames the visit
   as recognition addressed to Rwandans, not merely because the outlet is
   Rwandan.
6. **Narrator who is the host.** On `rwandan_govt` sources the institution
   narrates its own hosting; record narrator-as-host separately from
   journalist narration.
