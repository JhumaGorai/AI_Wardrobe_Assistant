from typing import Protocol

from app.schemas.garment import GarmentAnalysis


class VisionService(Protocol):
    async def analyze_garment(self, image_url: str) -> GarmentAnalysis:
        ...
