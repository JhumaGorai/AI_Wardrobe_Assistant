import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin

ALLOWED_FEEDBACK = ("like", "dislike", "save", "worn")


class OutfitFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "outfit_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "outfit_id", "feedback", name="uq_user_outfit_feedback"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    outfit_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("outfits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
