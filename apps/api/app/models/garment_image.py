import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, false
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin
from sqlalchemy import DateTime, func


class GarmentImage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "garment_images"

    garment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("garments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_type: Mapped[str] = mapped_column(String, default="original", server_default="original")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
