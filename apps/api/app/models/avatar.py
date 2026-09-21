import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, false
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Avatar(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "avatars"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String, default="full_body", server_default="full_body")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    avatar_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at = TimestampMixin.created_at
