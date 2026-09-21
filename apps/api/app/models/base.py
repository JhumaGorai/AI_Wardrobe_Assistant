"""Common column mixins shared by every model."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    # Generated client-side (uuid.uuid4) rather than relying solely on the DB's
    # gen_random_uuid() so the same model code works against Postgres in prod and
    # SQLite in tests. The Postgres migration still sets a matching server_default
    # as a safety net for rows inserted outside the ORM.
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
