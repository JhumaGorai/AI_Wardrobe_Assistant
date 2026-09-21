import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.core.database import Base
from app.models.base import UUIDPrimaryKeyMixin

settings = get_settings()


class GarmentEmbedding(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "garment_embeddings"

    garment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("garments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    # Dimension is read from settings at import time so it always matches EMBEDDING_DIMENSION.
    # The migration that creates this column reads the same env var — see alembic/versions.
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimension), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
