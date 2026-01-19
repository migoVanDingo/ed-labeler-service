from datetime import timedelta

from google.cloud import storage


def generate_signed_url(
    bucket_name: str,
    object_name: str,
    expires_seconds: int = 300,
) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires_seconds),
        method="GET",
    )
