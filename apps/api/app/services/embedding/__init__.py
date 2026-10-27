from app.core.config import get_settings
from app.services.embedding.base import EmbeddingService
from app.services.embedding.mock import MockEmbeddingService

_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Process-wide singleton, same pattern as app.services.vision/app.services.storage."""
    global _embedding_service
    if _embedding_service is None:
        provider = get_settings().embedding_provider
        if provider == "mock":
            _embedding_service = MockEmbeddingService()
        else:
            raise NotImplementedError(
                f"Unsupported embedding provider: {provider!r}. Only 'mock' is implemented so far."
            )
    return _embedding_service


__all__ = ["EmbeddingService", "MockEmbeddingService", "get_embedding_service"]
