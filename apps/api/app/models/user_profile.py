import uuid

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    height_cm: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    body_shape: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_fit: Mapped[str] = mapped_column(String, default="regular", server_default="regular")
    preferred_styles: Mapped[list] = mapped_column(JSON, default=list)
    preferred_colors: Mapped[list] = mapped_column(JSON, default=list)
    disliked_colors: Mapped[list] = mapped_column(JSON, default=list)
    style_preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship(back_populates="profile")
