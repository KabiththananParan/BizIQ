"""
app/schemas/datasource.py
Request/response models for Data Source CRUD, with input sanitisation.
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MAX_CONTENT_CHARS = 1_000_000

# Control characters except \t \n \r
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(value: str) -> str:
    """Strip control characters and surrounding whitespace."""
    return _CONTROL_RE.sub("", value).strip()


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    content: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    source_type: str = Field(default="text", min_length=1, max_length=50)

    @field_validator("name", "description", "content", "source_type")
    @classmethod
    def sanitize(cls, v: str) -> str:
        return clean_text(v)

    @field_validator("name", "content")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be blank")
        return v


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    content: Optional[str] = Field(default=None, min_length=1, max_length=MAX_CONTENT_CHARS)
    source_type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    status: Optional[Literal["active", "retired"]] = None

    @field_validator("name", "description", "content", "source_type")
    @classmethod
    def sanitize(cls, v: Optional[str]) -> Optional[str]:
        return clean_text(v) if v is not None else v

    @field_validator("name", "content")
    @classmethod
    def not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v:
            raise ValueError("must not be blank")
        return v


class DataSourceOut(BaseModel):
    id: int
    name: str
    description: str = ""
    source_type: str = "text"
    status: str = "active"
    uploaded_at: str

    @field_validator("description", "source_type", "status", mode="before")
    @classmethod
    def legacy_nulls(cls, v, info):
        """Rows from older databases may contain NULLs; fall back to defaults."""
        if v is None:
            return {"description": "", "source_type": "text", "status": "active"}[info.field_name]
        return v
