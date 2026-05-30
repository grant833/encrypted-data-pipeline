"""
S3 helper functions for the pipeline.

Wraps boto3 with project-specific defaults and simpler error handling.
Used by the upload script to push encrypted files to inbound buckets and
by the DAG to download incoming files and upload delivery confirmations.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_s3_client():
    """Build an S3 client using env-based AWS credentials."""
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


def upload_file(
    local_path: str,
    bucket: str,
    s3_key: Optional[str] = None,
    client=None,
) -> bool:
    """
    Upload a local file to S3.

    Args:
        local_path: Path to the file on disk
        bucket: Target S3 bucket name
        s3_key: Object key in S3 (defaults to filename if not provided)
        client: Optional pre-built S3 client

    Returns:
        True on success, False on failure
    """
    client = client or get_s3_client()
    s3_key = s3_key or Path(local_path).name

    try:
        client.upload_file(local_path, bucket, s3_key)
        logger.info(f"Uploaded {local_path} -> s3://{bucket}/{s3_key}")
        return True
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        return False


def download_file(
    bucket: str,
    s3_key: str,
    local_path: str,
    client=None,
) -> bool:
    """
    Download a file from S3 to a local path.

    Args:
        bucket: S3 bucket name
        s3_key: Object key in S3
        local_path: Where to write the file locally
        client: Optional pre-built S3 client

    Returns:
        True on success, False on failure
    """
    client = client or get_s3_client()

    # Ensure parent directory exists
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        client.download_file(bucket, s3_key, local_path)
        logger.info(f"Downloaded s3://{bucket}/{s3_key} -> {local_path}")
        return True
    except ClientError as e:
        logger.error(f"S3 download failed: {e}")
        return False


def list_objects(
    bucket: str,
    prefix: str = "",
    client=None,
) -> List[dict]:
    """
    List objects in a bucket, optionally filtered by prefix.

    Args:
        bucket: S3 bucket name
        prefix: Optional key prefix filter
        client: Optional pre-built S3 client

    Returns:
        List of dicts with keys: 'Key', 'Size', 'LastModified'
    """
    client = client or get_s3_client()

    try:
        kwargs = {"Bucket": bucket}
        if prefix:
            kwargs["Prefix"] = prefix
        response = client.list_objects_v2(**kwargs)
        return response.get("Contents", [])
    except ClientError as e:
        logger.error(f"S3 list failed: {e}")
        return []


def get_latest_object(
    bucket: str,
    prefix: str = "",
    client=None,
) -> Optional[dict]:
    """
    Find the most recently modified object in a bucket.

    Args:
        bucket: S3 bucket name
        prefix: Optional key prefix filter
        client: Optional pre-built S3 client

    Returns:
        Dict with 'Key', 'Size', 'LastModified' or None if bucket is empty
    """
    objects = list_objects(bucket, prefix, client)
    if not objects:
        return None
    return max(objects, key=lambda obj: obj["LastModified"])
