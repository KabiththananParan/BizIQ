"""Rule-based intent classification for the BizIQ NLP baseline.

The classifier is deliberately explainable: every prediction is based on a
small set of business-language patterns. It can later be replaced by an ML
classifier without changing the API contract.
"""
import re

INTENT_KEYWORDS = {
    "COMPARISON": [
        "compare", "comparison", "versus", "vs", "difference",
        "higher than", "lower than", "better than", "worse than"
    ],
    "RANKING": [
        "highest", "lowest", "top", "bottom", "maximum", "minimum",
        "most", "least", "best", "worst", "highest sales", "lowest sales",
        "highest revenue", "lowest revenue", "best selling", "top selling",
        "which product had the", "which region had the"
    ],
    "AGGREGATION": [
        "total", "sum", "overall", "average", "avg", "mean", "count",
        "number of", "how many", "how much"
    ],
    "FORECAST_REQUEST": [
        "forecast", "predict", "prediction", "future", "next month",
        "next quarter", "next year", "expected next"
    ],
    "TREND_ANALYSIS": [
        "trend", "over time", "growth", "decline", "increase", "decrease",
        "changed", "change", "increased", "decreased", "growing", "declining"
    ],
    "REGIONAL_ANALYSIS": [
        "region", "regional", "location", "branch", "city", "area",
        "by region", "by location", "by branch", "by city"
    ],
    "PRODUCT_ANALYSIS": [
        "product", "products", "item", "items", "sku", "product line"
    ],
    "REVENUE_ANALYSIS": [
        "revenue", "income", "earnings", "profit", "gross profit", "net profit"
    ],
    "SALES_ANALYSIS": [
        "sales", "sold", "selling", "sell", "units sold", "sales amount"
    ],
}


def _contains(text: str, phrase: str) -> bool:
    """Match whole words for short keywords and phrases safely."""
    pattern = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
    return re.search(pattern, text.lower()) is not None


def classify_intent(text: str) -> str:
    """Return the highest-confidence business intent.

    More specific/multi-word phrases receive a larger score so that, for
    example, 'highest sales' is classified as RANKING instead of SALES_ANALYSIS.
    """
    text = text.lower().strip()
    scores = {intent: 0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if _contains(text, keyword):
                # Longer phrases are more informative than single words.
                scores[intent] += 2 if " " in keyword else 1

    # Question patterns that strongly indicate an operation.
    if re.search(r"\bwhich\b.*\b(highest|lowest|top|bottom|best|worst|most|least)\b", text):
        scores["RANKING"] += 4
    if re.search(r"\bwhat is the total\b|\bwhat is the average\b|\bhow many\b|\bhow much\b", text):
        scores["AGGREGATION"] += 4
    if re.search(r"\bhow did .* change\b|\bhow has .* changed\b", text):
        scores["TREND_ANALYSIS"] += 4

    best_intent, best_score = max(scores.items(), key=lambda item: item[1])
    return best_intent if best_score > 0 else "UNKNOWN"
