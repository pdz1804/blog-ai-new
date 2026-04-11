from __future__ import annotations

import datetime

from google.cloud import storage  # pylint: disable=no-name-in-module

from app.config import get_settings

settings = get_settings()
_storage_client: storage.Client | None = None

def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=settings.gcp_project_id)
    return _storage_client

def generate_upload_signed_url_v4(bucket_name: str, blob_name: str, content_type: str = "image/jpeg", expiration_minutes: int = 15) -> str:
    """
    Generates a v4 signed URL for uploading a blob using HTTP PUT.
    Note: Your development environment or service account must have
    iam.serviceAccounts.signBlob permission to execute this successfully.
    """
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    url = blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(minutes=expiration_minutes),
        method="PUT",
        content_type=content_type,
    )
    return url
