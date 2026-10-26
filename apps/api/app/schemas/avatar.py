import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.image_validation import ALLOWED_IMAGE_CONTENT_TYPES as ALLOWED_AVATAR_CONTENT_TYPES
from app.core.image_validation import MAX_IMAGE_SIZE_BYTES as MAX_AVATAR_SIZE_BYTES

__all__ = ["ALLOWED_AVATAR_CONTENT_TYPES", "MAX_AVATAR_SIZE_BYTES", "AvatarRead"]


class AvatarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    image_url: str
    type: str
    is_primary: bool
    created_at: datetime
