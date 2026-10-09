"""PII redaction + prompt-injection detection, applied BEFORE data reaches the external LLM."""
import re
from typing import Any

PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "NIC": re.compile(r"\b\d{9}[VvXx]\b|\b\d{12}\b"),          # Sri Lankan NIC
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "PHONE": re.compile(r"(?<!\d)(?:\+94|0)\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d)"),
}
INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)|"
    r"disregard (the )?(system|previous)|reveal (your )?(system )?prompt|"
    r"you are now|act as|developer mode|jailbreak", re.I)


def redact_text(text: str) -> str:
    for label, pat in PATTERNS.items():
        text = pat.sub(f"[{label}_REDACTED]", text)
    return text


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def find_injection(value: Any) -> list[str]:
    """Return suspicious snippets found inside retrieved data."""
    hits: list[str] = []
    if isinstance(value, str):
        if INJECTION.search(value):
            hits.append(value[:80])
    elif isinstance(value, dict):
        for v in value.values():
            hits += find_injection(v)
    elif isinstance(value, list):
        for v in value:
            hits += find_injection(v)
    return hits
