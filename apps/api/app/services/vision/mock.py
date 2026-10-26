"""Mock vision provider -- no real AI/API key required (user's explicit "mocks for now" choice).
Deterministic per image_url (re-analyzing the same image always yields the same fake result) but
varied across different garments, via a per-call Random seeded from the URL -- no shared mutable
state, so a single instance is safe to reuse across requests."""
import random

from app.schemas.garment import ALLOWED_CATEGORIES, GarmentAnalysis

_SUBCATEGORIES: dict[str, list[str]] = {
    "top": ["t-shirt", "blouse", "shirt", "sweater", "tank top"],
    "bottom": ["jeans", "trousers", "shorts", "skirt"],
    "dress": ["maxi dress", "slip dress", "shirt dress"],
    "outerwear": ["jacket", "coat", "blazer", "cardigan"],
    "footwear": ["sneakers", "boots", "sandals", "heels"],
    "accessory": ["belt", "scarf", "hat", "bag"],
}
_COLORS = ["black", "white", "cream", "navy", "beige", "olive", "burgundy", "grey"]
_PATTERNS = ["solid", "striped", "floral", "checked", "plain"]
_MATERIALS = ["cotton", "linen", "wool", "denim", "polyester", "silk"]
_FITS = ["slim", "regular", "relaxed", "oversized"]
_SEASONS = ["spring", "summer", "fall", "winter"]
_STYLE_TAGS = ["minimalist", "elegant", "smart casual", "streetwear", "classic", "bohemian"]


class MockVisionService:
    async def analyze_garment(self, image_url: str) -> GarmentAnalysis:
        rng = random.Random(image_url)
        category = rng.choice(ALLOWED_CATEGORIES)
        subcategory = rng.choice(_SUBCATEGORIES[category])
        colors = rng.sample(_COLORS, k=rng.randint(1, 2))
        fit = rng.choice(_FITS)
        description = f"{fit} {' and '.join(colors)} {subcategory}"
        return GarmentAnalysis(
            category=category,
            subcategory=subcategory,
            colors=colors,
            pattern=rng.choice(_PATTERNS),
            material=rng.choice(_MATERIALS),
            fit=fit,
            formality=round(rng.uniform(0, 1), 2),
            seasons=rng.sample(_SEASONS, k=rng.randint(1, 2)),
            style_tags=rng.sample(_STYLE_TAGS, k=rng.randint(1, 3)),
            description=description,
        )
