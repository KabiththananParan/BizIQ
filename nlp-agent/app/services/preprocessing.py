import re
import unicodedata
from fastapi import HTTPException
from app.services import config


def sanitize_input(text: str) -> str:
    """Basic sanitization and validation of user input."""
    if text is None:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    text = text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    return text


def normalize_text(text: str) -> str:
    """Clean and normalize user text without changing its business meaning."""
    if text is None:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    # Normalize Unicode characters.
    text = unicodedata.normalize("NFKC", text)

    # Remove non-printable characters.
    text = "".join(
        ch for ch in text
        if ch.isprintable() or ch in "\n\t"
    )

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    if len(text) > config.MAX_QUERY_CHARS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Question is too long. "
                f"Maximum is {config.MAX_QUERY_CHARS} characters."
            )
        )

    return text