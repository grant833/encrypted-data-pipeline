"""
S3 helper functions for inbound polling and outbound delivery.
"""

import logging
from pathlib import Path
from typing import List, Optional

import boto3

logger = logging.getLogger(__name__)


def get_s3_client():
    """Return a boto3 S3 client using credentials from env."""
    # TODO: boto3.client("s3")
    raise NotImplementedError


def list_new_files(bucket: str, prefix: str = "", filename_pattern: str = None) -> List[str]:
    """
    List files in an S3 bucket matching an optional prefix and pattern.

    Args:
        bucket: S3 bucket name
        prefix: Optional key prefix filter
        filename_pattern: Optional substring pattern to match

    Returns:
        List of S3 keys
    """
    # TODO: list_objects_v2 with prefix
    # TODO: Filter by filename_pattern
    raise NotImplementedError


def download_file(bucket: str, key: str, local_path: str) -> bool:
    """Download an S3 object to a local path."""
    # TODO: s3.download_file(bucket, key, local_path)
    raise NotImplementedError


def upload_file(local_path: str, bucket: str, key: Optional[str] = None) -> bool:
    """Upload a local file to S3. Defaults key to filename if not provided."""
    # TODO: s3.upload_file(local_path, bucket, key)
    raise NotImplementedError


def archive_file(source_bucket: str, source_key: str, archive_bucket: str) -> bool:
    """Copy a file from inbound to archive bucket, then delete from source."""
    # TODO: Copy then delete
    raise NotImplementedError
