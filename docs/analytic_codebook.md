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
