from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.garment_image import GarmentImage


async def create(
    db: AsyncSession,
    *,
    garment_id: UUID,
    image_url: str,
    image_type: str = "original",
    is_primary: bool = True,
) -> GarmentImage:
    image = GarmentImage(
        garment_id=garment_id, image_url=image_url, image_type=image_type, is_primary=is_primary
    )
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


async def list_for_garment(db: AsyncSession, garment_id: UUID) -> list[GarmentImage]:
    result = await db.execute(
        select(GarmentImage).where(GarmentImage.garment_id == garment_id).order_by(GarmentImage.created_at.asc())
    )
    return list(result.scalars().all())
