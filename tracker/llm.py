"""Optional LLM-assisted extraction (requires `pip install anthropic` and the
ANTHROPIC_API_KEY environment variable). Output is stored in the local
database as a suggestion for the coder; it is never written to the public CSVs
automatically."""

import json
import os

from . import config

DEFAULT_MODEL = os.environ.get("TRACKER_MODEL", "claude-sonnet-5-5")

PROMPT = """You are helping code news articles for a dataset of foreign delegations
that visit Rwanda to learn from its institutions (study tours, study visits,
benchmarking visits).

Read the article and return ONLY a JSON object with these keys. Use null when
the article does not state something; do not guess.

- is_learning_visit: true if the article documents a delegation visiting Rwanda to learn or share experience
- start_date, end_date: ISO dates (YYYY-MM-DD) of the visit if stated
- visiting_country_iso3: ISO 3166-1 alpha-3 code of the sending country
- visiting_entity: institution(s) the delegation comes from
- entity_type: one of {entity_types}
- delegation_size: integer if stated
- lead: head of delegation with title
- themes: list drawn only from {themes}
- hgs_mentioned: list drawn only from {hgs} (only if named in the text)
- rwandan_hosts: Rwandan institutions met or visited
- rci_mentioned: true if Rwanda Cooperation or RCI is named
- co_facilitator: third parties that organised or funded the visit
- evidence: for each non-null field above, a short supporting phrase from the article (max 15 words)

Article title: {title}
Article text:
{text}
"""


def extract_with_llm(text: str, title: str = "", model: str = DEFAULT_MODEL) -> dict:
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit("Install the optional dependency first: pip install anthropic") from exc
    vocab = config.vocab()
    prompt = PROMPT.format(
        entity_types=", ".join(vocab["entity_type"]),
        themes=", ".join(vocab["themes"]),
        hgs=", ".join(vocab["hgs"]),
        title=title or "",
        text=text[:20000],
    )
    client = anthropic.Anthropic()
    msg = client.messages.create(model=model, max_tokens=1500,
                                 messages=[{"role": "user", "content": prompt}])
    raw = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {"error": "no JSON in response", "raw": raw[:500]}
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return {"error": "invalid JSON", "raw": raw[:500]}
