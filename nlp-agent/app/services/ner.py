"""Business-oriented Named Entity Recognition (NER)."""
import re

try:
    import spacy
except ImportError:  # pragma: no cover
    spacy = None


# Common business terms. These are project-specific entities rather than
# general-purpose NER labels.
BUSINESS_METRICS = {
    "sales", "revenue", "profit", "income", "orders", "customers",
    "products", "expenses", "cost", "quantity", "units", "earnings"
}

KNOWN_LOCATIONS = {
    "colombo", "kandy", "galle", "matara", "jaffna", "negombo",
    "kurunegala", "anuradhapura", "ratnapura", "badulla", "trincomalee",
    "batticaloa", "west", "east", "north", "south"
}

KNOWN_PRODUCTS = {"standard", "premium"}

MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
}

RELATIVE_PERIODS = [
    "last month", "this month", "next month", "last quarter", "this quarter",
    "next quarter", "last year", "this year", "next year"
]


def _load_spacy():
    if spacy is None:
        return None
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        return None


NLP = _load_spacy()


def _add_unique(entities, text, entity_type):
    text = text.strip(" .,!?;:")
    if not text:
        return
    key = (text.lower(), entity_type)
    if not any((e["text"].lower(), e["type"]) == key for e in entities):
        entities.append({"text": text, "type": entity_type})


def extract_entities(text: str):
    entities = []
    lower = text.lower()

    # ------------------------------------------------------------------
    # 1. Relative time periods: spaCy may miss phrases such as 'last month'.
    # ------------------------------------------------------------------
    for period in RELATIVE_PERIODS:
        if re.search(r"(?<!\w)" + re.escape(period) + r"(?!\w)", lower):
            _add_unique(entities, period, "TIME_PERIOD")

    # ------------------------------------------------------------------
    # 2. Months such as January and February.
    # ------------------------------------------------------------------
    for month in MONTHS:
        if re.search(r"(?<!\w)" + re.escape(month) + r"(?!\w)", lower):
            _add_unique(entities, month.title(), "TIME_PERIOD")

    # ------------------------------------------------------------------
    # 3. Years such as 2025 and 2026.
    # ------------------------------------------------------------------
    for year in re.findall(r"\b(?:19|20)\d{2}\b", text):
        _add_unique(entities, year, "TIME_PERIOD")

    # ------------------------------------------------------------------
    # 4. Quarters such as Q1, Q2, Q3, Q4.
    # ------------------------------------------------------------------
    for match in re.finditer(r"\bQ[1-4]\b", text, flags=re.IGNORECASE):
        _add_unique(entities, match.group(0).upper(), "QUARTER")

    # ------------------------------------------------------------------
    # 5. Business-specific locations and regions.
    # ------------------------------------------------------------------
    for word in re.findall(r"\b[A-Za-z]+\b", text):
        if word.lower() in KNOWN_LOCATIONS:
            entity_type = "REGION" if word.lower() in {"west", "east", "north", "south"} else "LOCATION"
            _add_unique(entities, word.title(), entity_type)

    # ------------------------------------------------------------------
    # 6. Business metrics.
    # ------------------------------------------------------------------
    for metric in sorted(BUSINESS_METRICS, key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(metric) + r"(?!\w)", lower):
            _add_unique(entities, metric, "METRIC")

    # ------------------------------------------------------------------
    # 7. Known products from the sample/business data.
    # ------------------------------------------------------------------
    for product in KNOWN_PRODUCTS:
        if re.search(r"(?<!\w)" + re.escape(product) + r"(?!\w)", lower):
            _add_unique(entities, product.title(), "PRODUCT")

    # ------------------------------------------------------------------
    # 8. General spaCy entities when the model is installed.
    # ------------------------------------------------------------------
    if NLP is not None:
        doc = NLP(text)
        for ent in doc.ents:
            if ent.label_ == "DATE":
                _add_unique(entities, ent.text, "TIME_PERIOD")
            elif ent.label_ in {"GPE", "LOC"}:
                # Avoid duplicating known locations.
                _add_unique(entities, ent.text, "LOCATION")
            elif ent.label_ in {"MONEY", "PERCENT", "CARDINAL", "QUANTITY"}:
                _add_unique(entities, ent.text, ent.label_)

    return entities


def entities_to_ir_format(entities: list[dict]) -> dict[str, list[str]]:
    """Convert NLP output to Member 2's agreed IR request shape."""
    result: dict[str, list[str]] = {}
    mapping = {
        "LOCATION": "location",
        "REGION": "region",
        "METRIC": "metric",
        "TIME_PERIOD": "time_period",
        "QUARTER": "quarter",
        "PRODUCT": "product",
    }
    for entity in entities:
        key = mapping.get(entity["type"])
        if key:
            result.setdefault(key, []).append(entity["text"])
    return result
