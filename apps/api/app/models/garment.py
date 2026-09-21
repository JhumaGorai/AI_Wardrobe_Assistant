import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Numeric, String, Text, true
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

CATEGORIES = ("top", "bottom", "dress", "outerwear", "footwear", "accessory")


class Garment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "garments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    colors: Mapped[list] = mapped_column(JSON, default=list)
    pattern: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    fit: Mapped[str | None] = mapped_column(String, nullable=True)
    formality: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    seasons: Mapped[list] = mapped_column(JSON, default=list)
    style_tags: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String, default="pending", server_default="pending", index=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
