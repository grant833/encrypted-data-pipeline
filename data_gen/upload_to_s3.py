"""
Simulate a vendor encrypting and delivering a file.

Currently writes to a local inbound/ directory. When AWS S3 is set up in
Phase 2, this will be updated to upload the encrypted file to the inbound
S3 bucket instead.

Usage:
    python data_gen/upload_to_s3.py --file ./data/customer_applications_20260523.txt
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from pipeline.encryption import encrypt_file

load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="Path to plaintext file")
    parser.add_argument(
        "--inbound-dir",
        default="/home/grant/pipeline-project/data/inbound",
        help="Destination directory for encrypted files",
    )
    args = parser.parse_args()

    input_path = Path(args.file)
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    inbound_key = os.getenv("GPG_INBOUND_KEY_ID")
    if not inbound_key:
        print("GPG_INBOUND_KEY_ID not set in environment")
        sys.exit(1)

    # Make sure inbound dir exists
    inbound_dir = Path(args.inbound_dir)
    inbound_dir.mkdir(parents=True, exist_ok=True)

    # Encrypt to a .pgp file in the inbound directory
    output_path = inbound_dir / (input_path.name + ".pgp")

    print(f"Encrypting {input_path.name} with key {inbound_key}...")
    ok = encrypt_file(str(input_path), str(output_path), inbound_key)
    if not ok:
        print("Encryption failed")
        sys.exit(1)

    encrypted_size = output_path.stat().st_size
    print(f"Encrypted file written: {output_path}")
    print(f"  Size: {encrypted_size:,} bytes")
    print(f"  First 20 bytes (hex): {output_path.read_bytes()[:20].hex()}")
    print(f"\nReady for pipeline ingestion.")


if __name__ == "__main__":
    main()
