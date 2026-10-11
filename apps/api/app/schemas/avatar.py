import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

ALLOWED_AVATAR_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class AvatarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    image_url: str
    type: str
    is_primary: bool
    created_at: datetime
