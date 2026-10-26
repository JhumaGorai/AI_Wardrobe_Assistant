import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_CATEGORIES = ("top", "bottom", "dress", "outerwear", "footwear", "accessory")


def _validate_category(value: str | None) -> str | None:
    if value is not None and value not in ALLOWED_CATEGORIES:
        raise ValueError(f"category must be one of {ALLOWED_CATEGORIES}, got {value!r}")
    return value


class GarmentAnalysis(BaseModel):
    """Validated shape of a vision provider's analysis of a garment image (CLAUDE.md sec 5/
    IMPLEMENTATION_PROMPT.md Phase 7). Constructing this from raw provider output is the single
    point where bad AI data gets caught: a `ValidationError` here never reaches the database --
    app/services/garment_processor.py catches it and records processing_status="failed" with a
    safe message instead."""

    category: str
    subcategory: str | None = None
    colors: list[str] = Field(default_factory=list)
    pattern: str | None = None
    material: str | None = None
    fit: str | None = None
    formality: float = Field(ge=0, le=1)
    seasons: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    description: str

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str) -> str:
        return _validate_category(value)  # type: ignore[return-value]


class GarmentImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_url: str
    image_type: str
    is_primary: bool
    width: int | None
    height: int | None
    created_at: datetime


class GarmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str | None
    category: str | None
    subcategory: str | None
    colors: list
    pattern: str | None
    material: str | None
    fit: str | None
    formality: float | None
    seasons: list
    style_tags: list
    description: str | None
    processing_status: str
    processing_error: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[GarmentImageRead] = Field(default_factory=list)

    @classmethod
    def from_model(cls, garment: Any, images: list[Any]) -> "GarmentRead":
        """`images` isn't an ORM relationship on Garment (kept out deliberately to avoid async
        lazy-loading pitfalls) -- callers fetch it separately via garment_image_repository and
        attach it here."""
        base = cls.model_validate(garment)
        return base.model_copy(update={"images": [GarmentImageRead.model_validate(i) for i in images]})


class GarmentUpdate(BaseModel):
    """Every field is optional and only the ones actually provided are applied (see
    garment_repository.update_fields, which uses exclude_unset=True) -- most garment attributes
    are normally filled in automatically by vision analysis, so PUT is typically used to correct
    one or two fields, not resubmit the whole object."""

    name: str | None = None
    category: str | None = None
    subcategory: str | None = None
    colors: list[str] | None = None
    pattern: str | None = None
    material: str | None = None
    fit: str | None = None
    formality: float | None = Field(default=None, ge=0, le=1)
    seasons: list[str] | None = None
    style_tags: list[str] | None = None
    description: str | None = None

    @field_validator("category")
    @classmethod
    def category_allowed(cls, value: str | None) -> str | None:
        return _validate_category(value)
