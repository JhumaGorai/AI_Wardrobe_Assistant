from app.core.config import get_settings
from app.services.vision.base import VisionService
from app.services.vision.mock import MockVisionService

_vision_service: VisionService | None = None


def get_vision_service() -> VisionService:
    """Returns a process-wide singleton, same pattern as app.services.storage. A FastAPI
    dependency (app/core/deps_processing.py) wraps this for the background processor so tests
    can override it without touching a real provider."""
    global _vision_service
    if _vision_service is None:
        provider = get_settings().vision_provider
        if provider == "mock":
            _vision_service = MockVisionService()
        else:
            raise NotImplementedError(
                f"Unsupported vision provider: {provider!r}. Only 'mock' is implemented so far."
            )
    return _vision_service


__all__ = ["VisionService", "MockVisionService", "get_vision_service"]
