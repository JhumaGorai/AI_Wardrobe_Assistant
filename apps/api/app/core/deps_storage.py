"""Split into its own module (rather than deps.py) purely so app.services.storage's boto3 import
doesn't get pulled into every module that imports app.core.deps for auth."""
from app.services.storage import StorageService, get_storage_service


def storage_dependency() -> StorageService:
    return get_storage_service()
