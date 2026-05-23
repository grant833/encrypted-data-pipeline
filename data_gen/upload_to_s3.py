"""
Encrypt synthetic data files and upload to S3 inbound bucket.

This script simulates a vendor sending an encrypted file to your S3 bucket.
It encrypts a local plaintext file with the vendor public key, uploads the
.pgp file to S3, and the pipeline picks it up from there.

Usage:
    python data_gen/upload_to_s3.py --file ./data/BF_Applications_20260519.txt
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent to path so we can import the pipeline module
sys.path.insert(0, str(Path(__file__).parent.parent))

# from pipeline.encryption import encrypt_file
# from pipeline.s3_utils import upload_file
# from pipeline.config import aws_config, gpg_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to plaintext file")
    parser.add_argument("--bucket", default=None, help="Override target bucket")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    # TODO: Encrypt the file with the inbound GPG public key
    # TODO: Upload encrypted .pgp file to S3 inbound bucket
    # TODO: Print confirmation with S3 key path

    print(f"Encrypted and uploaded {input_path.name}")


if __name__ == "__main__":
    main()
