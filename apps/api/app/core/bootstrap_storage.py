"""Ensures the object storage bucket exists and is readable, run once at container startup
(see entrypoint.sh) before the API starts serving requests.

This exists instead of a separate `minio/mc` init container because, as of this project's build
date (Sept 2026), MinIO stopped publishing free Docker images to Docker Hub entirely, and the
community's quay.io mirror situation is a moving target — safer to depend on boto3 (already a
real dependency) than on a second external image whose availability/tag we can't fully verify
from this environment. This only needs the `minio` server image itself.

For a real S3 deployment (not local MinIO), the bucket would normally be provisioned by
infra-as-code instead of by the app — this bootstrap step is dev-convenience, not a production
pattern.
"""
import json
import time

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


def ensure_bucket(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    settings = get_settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.storage_endpoint,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        region_name=settings.storage_region,
        use_ssl=settings.storage_use_ssl,
        config=Config(s3={"addressing_style": "path"}),
    )

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            try:
                client.head_bucket(Bucket=settings.storage_bucket)
            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code")
                if error_code in ("404", "NoSuchBucket"):
                    client.create_bucket(Bucket=settings.storage_bucket)
                else:
                    raise

            # Equivalent to `mc anonymous set download` — see the known-limitation note in
            # app/services/storage/s3.py about this being permanent public read, not presigned.
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{settings.storage_bucket}/*"],
                    }
                ],
            }
            client.put_bucket_policy(Bucket=settings.storage_bucket, Policy=json.dumps(policy))
            print(f"Storage bucket '{settings.storage_bucket}' is ready.")
            return
        except Exception as exc:  # noqa: BLE001 - includes connection errors while minio boots
            last_error = exc
            print(f"[{attempt}/{max_attempts}] object storage not ready yet ({exc}); retrying...")
            time.sleep(delay_seconds)

    raise RuntimeError(f"Could not reach object storage after {max_attempts} attempts: {last_error}")


if __name__ == "__main__":
    ensure_bucket()
