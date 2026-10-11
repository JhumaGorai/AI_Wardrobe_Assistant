"""S3-compatible storage (works against real AWS S3 or a local MinIO instance).

boto3 is sync-only, so calls are run in a thread via asyncio.to_thread rather than blocking the
event loop. This is the only file in the codebase that imports boto3.
"""
import asyncio
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()


class S3StorageService:
    def __init__(self) -> None:
        self._bucket = settings.storage_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
            use_ssl=settings.storage_use_ssl,
            # MinIO (and most non-AWS S3-compatible services) need path-style addressing
            # (http://host/bucket/key) rather than AWS's default virtual-hosted-style
            # (http://bucket.host/key), which requires DNS wildcarding we don't have locally.
            config=Config(s3={"addressing_style": "path"}),
        )

    def _put_object_sync(self, file: BinaryIO, key: str, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=file, ContentType=content_type)

    def _delete_object_sync(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    async def upload(self, file: BinaryIO, key: str, content_type: str) -> str:
        await asyncio.to_thread(self._put_object_sync, file, key, content_type)
        # NOTE (MVP simplification): returns a plain, permanent public URL rather than a
        # presigned/expiring one. The docker-compose MinIO setup makes the bucket
        # anonymously readable to match. This is fine for local dev but is NOT
        # access-controlled — anyone with a garment/avatar URL can view it. Revisit with
        # presigned URLs before this goes anywhere near production.
        return f"{settings.storage_public_url}/{self._bucket}/{key}"

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_object_sync, key)
