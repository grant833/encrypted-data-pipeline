"""
Simulate a vendor encrypting and delivering a file to the inbound S3 bucket.

This script:
  1. Encrypts the plaintext input file with the inbound public key (GPG)
  2. Uploads the encrypted .pgp file to the S3 inbound bucket
  3. Cleans up the local temp encrypted file

Usage:
    python data_gen/upload_to_s3.py --file ./data/customer_applications_20260523.txt
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from pipeline.encryption import encrypt_file
from pipeline.s3_utils import upload_file

load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to plaintext file")
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    inbound_key = os.getenv("GPG_INBOUND_KEY_ID")
    inbound_bucket = os.getenv("S3_INBOUND_BUCKET")
    if not inbound_key:
        print("GPG_INBOUND_KEY_ID not set in environment")
        sys.exit(1)
    if not inbound_bucket:
        print("S3_INBOUND_BUCKET not set in environment")
        sys.exit(1)

    # Encrypt to a temp .pgp file
    with tempfile.NamedTemporaryFile(
        suffix=".pgp",
        delete=False,
        dir="/tmp",
    ) as tmp:
        encrypted_tmp = tmp.name

    print(f"Encrypting {input_path.name} with key {inbound_key}...")
    ok = encrypt_file(str(input_path), encrypted_tmp, inbound_key)
    if not ok:
        print("Encryption failed")
        sys.exit(1)

    encrypted_size = os.path.getsize(encrypted_tmp)
    print(f"  Encrypted size: {encrypted_size:,} bytes")

    # Upload to S3
    s3_key = input_path.name + ".pgp"
    print(f"Uploading to s3://{inbound_bucket}/{s3_key}...")
    ok = upload_file(encrypted_tmp, inbound_bucket, s3_key)
    if not ok:
        print("Upload failed")
        os.unlink(encrypted_tmp)
        sys.exit(1)

    # Cleanup temp file
    os.unlink(encrypted_tmp)
    print(f"\n✓ Encrypted file delivered to s3://{inbound_bucket}/{s3_key}")
    print("  Ready for pipeline ingestion.")


if __name__ == "__main__":
    main()
