"""Turn fetched HTML into text, score relevance, and pre-fill visit fields.

Everything here produces *suggestions* for a human coder. Rule-based extraction
is deterministic and runs offline; tracker.llm offers an optional second pass.
"""

import json
import re
from datetime import date

import pycountry
import trafilatura
from dateutil import parser as dateparser

from . import config

# ------------------------------------------------------------------ text
def html_to_record(html: str, url: str | None = None) -> dict:
    """Extract main text and metadata. Returns keys: title, date, text, language."""
    out = trafilatura.extract(html, url=url, output_format="json", with_metadata=True,
                              include_comments=False, include_tables=False)
    if not out:
        return {"title": None, "date": None, "text": "", "language": None}
    data = json.loads(out)
    return {"title": data.get("title"), "date": data.get("date"),
            "text": data.get("text") or "", "language": data.get("language")}


# ------------------------------------------------------------- relevance
def relevance(text: str, title: str = "", visit_terms: list[str] | None = None) -> float:
    """0 if not about a learning visit to Rwanda; otherwise a rough 0-1 score."""
    visit_terms = visit_terms or config.sources()["visit_terms"]
    blob = f"{title}\n{text}".lower()
    if "rwanda" not in blob:
        return 0.0
    hits = sum(blob.count(t) for t in visit_terms)
    if hits == 0:
        return 0.0
    score = min(1.0, 0.4 + 0.15 * hits)
    if "delegation" in blob:
        score = min(1.0, score + 0.1)
    if any(t in (title or "").lower() for t in visit_terms):
        score = min(1.0, score + 0.2)
    return round(score, 2)


# ------------------------------------------------------------- countries
# Demonyms that pycountry does not resolve, focused on likely visitors.
DEMONYMS = {
    "nigerian": "NGA", "ghanaian": "GHA", "kenyan": "KEN", "ugandan": "UGA",
    "tanzanian": "TZA", "zambian": "ZMB", "zimbabwean": "ZWE", "malawian": "MWI",
    "namibian": "NAM", "ethiopian": "ETH", "somali": "SOM", "south sudanese": "SSD",
    "sudanese": "SDN", "liberian": "LBR", "sierra leonean": "SLE", "senegalese": "SEN",
    "gambian": "GMB", "beninese": "BEN", "togolese": "TGO", "malian": "MLI",
    "burkinabe": "BFA", "nigerien": "NER", "chadian": "TCD", "cameroonian": "CMR",
    "congolese": "COD", "gabonese": "GAB", "angolan": "AGO", "mozambican": "MOZ",
    "botswanan": "BWA", "motswana": "BWA", "basotho": "LSO", "lesotho": "LSO",
    "swazi": "SWZ", "eswatini": "SWZ", "south african": "ZAF", "egyptian": "EGY",
    "moroccan": "MAR", "tunisian": "TUN", "algerian": "DZA", "ivorian": "CIV",
    "burundian": "BDI", "djiboutian": "DJI", "eritrean": "ERI", "comorian": "COM",
    "malagasy": "MDG", "mauritian": "MUS", "seychellois": "SYC", "guinean": "GIN",
    "indian": "IND", "bangladeshi": "BGD", "sri lankan": "LKA", "pakistani": "PAK",
    "nepali": "NPL", "nepalese": "NPL", "qatari": "QAT", "emirati": "ARE",
    "british": "GBR", "american": "USA", "chinese": "CHN", "japanese": "JPN",
    "korean": "KOR", "timorese": "TLS", "argentine": "ARG", "argentinian": "ARG",
    "brazilian": "BRA", "haitian": "HTI", "jamaican": "JAM", "turkish": "TUR",
}
COUNTRY_ALIASES = {"ivory coast": "CIV", "cote d'ivoire": "CIV", "drc": "COD",
                   "dr congo": "COD", "uk": "GBR", "united states": "USA",
                   "timor-leste": "TLS", "east timor": "TLS", "the gambia": "GMB"}


def _country_names() -> dict[str, str]:
    names = {}
    for c in pycountry.countries:
        for attr in ("name", "common_name", "official_name"):
            val = getattr(c, attr, None)
            if val:
                names[val.lower()] = c.alpha_3
    names.update(COUNTRY_ALIASES)
    names.update(DEMONYMS)
    names.pop("rwanda", None)
    names.pop("rwandan", None)
    return names


_COUNTRY_RE = None


def countries_mentioned(text: str) -> list[str]:
    """ISO3 codes in order of first mention (Rwanda excluded)."""
    global _COUNTRY_RE
    names = _country_names()
    if _COUNTRY_RE is None:
        alts = sorted(names, key=len, reverse=True)
        _COUNTRY_RE = re.compile(r"\b(" + "|".join(re.escape(a) for a in alts) + r")\b", re.I)
    seen = []
    for m in _COUNTRY_RE.finditer(text):
        code = names[m.group(1).lower()]
        if code not in seen:
            seen.append(code)
    return seen


def likely_visiting_country(text: str, title: str = "") -> str | None:
    """Prefer a country named in the title, else the first in the text."""
    for blob in (title or "", text):
        found = countries_mentioned(blob)
        if found:
            return found[0]
    return None


# ----------------------------------------------------------------- dates
MONTHS = ("january|february|march|april|may|june|july|august|september|october|"
          "november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")
DASH = r"\s*(?:-|–|—|to|until|through)\s*"
RANGE_PATTERNS = [
    # 28 September to 4 October 2025
    re.compile(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})\.?{DASH}(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})\.?,?\s+(\d{{4}})", re.I),
    # 1-6 June 2026 / 23 - 29 June 2024 / 18-25 May 2019
    re.compile(rf"(\d{{1,2}})(?:st|nd|rd|th)?{DASH}(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTHS})\.?,?\s+(\d{{4}})", re.I),
    # September 28 to October 4, 2025
    re.compile(rf"({MONTHS})\.?\s+(\d{{1,2}}){DASH}({MONTHS})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})", re.I),
    # June 1-6, 2026
    re.compile(rf"({MONTHS})\.?\s+(\d{{1,2}}){DASH}(\d{{1,2}}),?\s+(\d{{4}})", re.I),
]


def _d(day, month, year) -> date | None:
    try:
        return dateparser.parse(f"{day} {month} {year}").date()
    except (ValueError, OverflowError):
        return None


def date_range(text: str) -> tuple[str | None, str | None]:
    for i, pat in enumerate(RANGE_PATTERNS):
        m = pat.search(text)
        if not m:
            continue
        g = m.groups()
        if i == 0:
            start, end = _d(g[0], g[1], g[4]), _d(g[2], g[3], g[4])
        elif i == 1:
            start, end = _d(g[0], g[2], g[3]), _d(g[1], g[2], g[3])
        elif i == 2:
            start, end = _d(g[1], g[0], g[4]), _d(g[3], g[2], g[4])
        else:
            start, end = _d(g[1], g[0], g[3]), _d(g[2], g[0], g[3])
        if start and end:
            if end < start:  # range crossing a year boundary
                start = start.replace(year=start.year - 1)
            return start.isoformat(), end.isoformat()
    return None, None


# ------------------------------------------------------------------ size
SIZE_PATTERNS = [
    re.compile(r"delegation of (\d{1,3})\b", re.I),
    re.compile(r"\b(\d{1,3})[- ]member delegation", re.I),
    re.compile(r"\b(\d{1,3}) (?:senior |student |high-level )?(?:officers|officials|delegates|students|"
               r"mayors|members|participants|legislators|mps)\b", re.I),
]


def delegation_size(text: str) -> int | None:
    for pat in SIZE_PATTERNS:
        m = pat.search(text)
        if m:
            n = int(m.group(1))
            if 1 < n < 500:
                return n
    return None


# -------------------------------------------------------- themes and HGS
THEME_KEYWORDS = {
    "governance_accountability": ["governance", "accountability", "anti-corruption", "ombudsman", "audit"],
    "public_service_reform": ["public service", "public sector reform", "civil service", "performance management"],
    "decentralization_local_govt": ["decentrali", "local government", "district", "mayor"],
    "finance_pfm": ["public financial management", "revenue", "budget", "fiscal", "tax"],
    "social_protection": ["social protection", "vup", "graduation", "cash transfer", "ubudehe"],
    "health": ["health", "vaccin", "hospital", "mutuelle", "community health"],
    "education": ["education", "school", "university", "tvet"],
    "digital_govt_ict": ["digital", "ict", "irembo", "e-government", "innovation"],
    "justice": ["justice", "judiciary", "court", "abunzi"],
    "peace_reconciliation": ["reconciliation", "peacebuilding", "unity", "post-conflict", "genocide"],
    "security_defence": ["defence", "defense", "military", "security", "police", "rdf"],
    "economy_investment": ["investment", "doing business", "economic", "private sector", "rdb"],
    "agriculture": ["agricultur", "dairy", "girinka", "farm", "crop"],
    "environment_urban": ["environment", "waste", "urban", "climate", "wetland", "model village", "plastic"],
    "tourism": ["tourism", "ecotourism", "conservation"],
    "aviation_transport": ["aviation", "airline", "transport", "rwandair"],
    "foreign_policy": ["foreign policy", "diplomacy", "bilateral"],
    "national_identity_unity": ["national identity", "ndi umunyarwanda", "itorero", "unity and reconciliation"],
    "leadership": ["leadership"],
    "youth": ["youth"],
    "gender": ["gender", "women"],
}
HGS_KEYWORDS = {
    "Umuganda": ["umuganda"], "Imihigo": ["imihigo", "performance contract"],
    "Girinka": ["girinka", "one cow per"], "Ubudehe": ["ubudehe"], "Abunzi": ["abunzi"],
    "Gacaca": ["gacaca"], "Itorero": ["itorero"], "Umushyikirano": ["umushyikirano"],
    "Umwiherero": ["umwiherero"], "Umugoroba w'Ababyeyi": ["umugoroba"],
    "Ndi Umunyarwanda": ["ndi umunyarwanda"], "Mutuelle de Sante": ["mutuelle"],
    "VUP": ["vision 2020 umurenge", " vup "], "IDP model village": ["model village"],
}


def tag(text: str, mapping: dict[str, list[str]]) -> list[str]:
    blob = f" {text.lower()} "
    return [label for label, kws in mapping.items() if any(k in blob for k in kws)]


# ---------------------------------------------------------- hosts and RCI
HOSTS = {
    "Rwanda Cooperation": [r"rwanda cooperation", r"\bRCI\b"],
    "Rwanda Governance Board": [r"rwanda governance board", r"\bRGB\b"],
    "Rwanda Development Board": [r"rwanda development board", r"\bRDB\b"],
    "Rwanda Revenue Authority": [r"rwanda revenue authority", r"\bRRA\b"],
    "MINALOC": [r"ministry of local government", r"\bMINALOC\b"],
    "MINECOFIN": [r"ministry of finance and economic planning", r"\bMINECOFIN\b"],
    "MIFOTRA": [r"ministry of public service and labour", r"\bMIFOTRA\b"],
    "MINIJUST": [r"ministry of justice", r"\bMINIJUST\b"],
    "MININTER": [r"ministry of interior", r"\bMININTER\b"],
    "MINUBUMWE": [r"ministry of national unity", r"\bMINUBUMWE\b"],
    "MINEDUC": [r"ministry of education", r"\bMINEDUC\b"],
    "Ministry of Health": [r"ministry of health", r"\bMINISANTE\b", r"\bRBC\b"],
    "Ministry of Defence / RDF": [r"rwanda defence force", r"ministry of defence", r"\bRDF\b"],
    "Office of the Auditor General": [r"auditor general", r"\bOAG\b"],
    "Office of the Ombudsman": [r"ombudsman"],
    "National Bank of Rwanda": [r"national bank of rwanda", r"\bBNR\b"],
    "RALGA": [r"\bRALGA\b", r"rwandan association of local government"],
    "City of Kigali": [r"city of kigali"],
    "Parliament of Rwanda": [r"parliament of rwanda", r"chamber of deputies", r"rwandan parliament"],
    "Kigali Genocide Memorial": [r"kigali genocide memorial"],
    "Rwanda Peace Academy": [r"rwanda peace academy"],
}
# Acronym patterns (written in capitals) are case-sensitive so that e.g. "rdb"
# inside a URL slug does not match; full names are case-insensitive.
_HOST_RE = {name: [re.compile(p, 0 if any(c.isupper() for c in p) else re.I) for p in pats]
            for name, pats in HOSTS.items()}


def hosts_mentioned(text: str) -> list[str]:
    return [name for name, pats in _HOST_RE.items() if any(p.search(text) for p in pats)]


def rci_involvement(text: str) -> str:
    return "explicit" if "Rwanda Cooperation" in hosts_mentioned(text) else "not_mentioned"


# --------------------------------------------------------------- combine
def extract_fields(text: str, title: str = "") -> dict:
    """Rule-based pre-fill for one article. Every value needs human review."""
    start, end = date_range(text)
    full = f"{title}\n{text}"
    return {
        "start_date": start,
        "end_date": end,
        "visiting_country_iso3": likely_visiting_country(text, title),
        "other_countries": countries_mentioned(full)[1:6],
        "delegation_size": delegation_size(full),
        "themes": tag(full, THEME_KEYWORDS),
        "hgs_mentioned": tag(full, HGS_KEYWORDS),
        "rwandan_hosts": hosts_mentioned(full),
        "rci_involvement": rci_involvement(full),
    }
