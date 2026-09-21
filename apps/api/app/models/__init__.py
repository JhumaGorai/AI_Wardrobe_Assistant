"""Import every model here so Alembic's autogenerate and Base.metadata see the full schema."""
from app.models.avatar import Avatar
from app.models.garment import Garment
from app.models.garment_embedding import GarmentEmbedding
from app.models.garment_image import GarmentImage
from app.models.outfit import Outfit
from app.models.outfit_feedback import OutfitFeedback
from app.models.outfit_item import OutfitItem
from app.models.style_request import StyleRequest
from app.models.try_on_job import TryOnJob
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = [
    "Avatar",
    "Garment",
    "GarmentEmbedding",
    "GarmentImage",
    "Outfit",
    "OutfitFeedback",
    "OutfitItem",
    "StyleRequest",
    "TryOnJob",
    "User",
    "UserProfile",
]
