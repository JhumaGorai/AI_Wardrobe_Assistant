from app.services.storage.base import StorageService
from app.services.storage.s3 import S3StorageService

_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    """Returns a process-wide singleton. A FastAPI dependency wraps this for request handlers
    so tests can override it (see tests/conftest.py) without touching real object storage."""
    global _storage_service
    if _storage_service is None:
        _storage_service = S3StorageService()
    return _storage_service


__all__ = ["StorageService", "S3StorageService", "get_storage_service"]
