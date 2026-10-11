import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfileUpdate(BaseModel):
    height_cm: float | None = Field(default=None, gt=50, lt=300)
    body_shape: str | None = None
    preferred_fit: str = "regular"
    preferred_styles: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    disliked_colors: list[str] = Field(default_factory=list)
    style_preferences: dict = Field(default_factory=dict)


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    height_cm: float | None
    body_shape: str | None
    preferred_fit: str
    preferred_styles: list
    preferred_colors: list
    disliked_colors: list
    style_preferences: dict
    created_at: datetime
    updated_at: datetime
