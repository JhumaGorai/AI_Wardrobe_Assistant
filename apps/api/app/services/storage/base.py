"""Object storage interface. Nothing outside app/services/storage/ should import boto3 (or any
other provider SDK) directly — route handlers and repositories depend on this Protocol only."""
from typing import BinaryIO, Protocol


class StorageService(Protocol):
    async def upload(self, file: BinaryIO, key: str, content_type: str) -> str:
        """Uploads `file` under `key` and returns a URL the frontend can load the image from."""
        ...

    async def delete(self, key: str) -> None: ...
