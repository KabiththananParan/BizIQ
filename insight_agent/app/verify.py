"""Numeric grounding check: every number the LLM writes must come from our computed stats."""
import re

NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def ungrounded_numbers(text: str, allowed: list[float]) -> list[str]:
    allowed_abs = {abs(a) for a in allowed}
    bad = []
    for m in NUM.findall(text):
        try:
            v = abs(float(m.replace(",", "").rstrip(".")))
        except ValueError:
            continue
        if 1900 <= v <= 2100 or v <= 12:       # years and small counts (e.g. "Q3", "3 months")
            continue
        if not any(abs(v - a) <= max(0.51, a * 0.01) for a in allowed_abs):
            bad.append(m)
    return bad
