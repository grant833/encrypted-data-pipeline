"""
GPG encryption and decryption for pipeline files.

Handles:
    - Decrypting inbound files using the pipeline's private key
    - Encrypting outbound files with the destination's public key

Wraps python-gnupg with a simpler interface and proper error handling.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import gnupg

logger = logging.getLogger(__name__)


def get_gpg_client(gnupg_home: Optional[str] = None) -> gnupg.GPG:
    """
    Initialize a GPG client.

    Args:
        gnupg_home: Path to GPG home directory (defaults to ~/.gnupg)

    Returns:
        Configured gnupg.GPG client
    """
    home = gnupg_home or os.path.expanduser("~/.gnupg")
    return gnupg.GPG(gnupghome=home)


def encrypt_file(
    input_path: str,
    output_path: str,
    recipient_key_id: str,
    always_trust: bool = True,
    gpg: Optional[gnupg.GPG] = None,
) -> bool:
    """
    Encrypt a file using the recipient's public key.

    Args:
        input_path: Path to the plaintext file
        output_path: Path where the encrypted .pgp file will be written
        recipient_key_id: Short or long key ID of the recipient
        always_trust: Skip web-of-trust check (needed for keys you generated)
        gpg: Optional GPG client (created fresh if not provided)

    Returns:
        True on success, False on failure
    """
    gpg = gpg or get_gpg_client()

    if not Path(input_path).exists():
        logger.error(f"Input file not found: {input_path}")
        return False

    with open(input_path, "rb") as f:
        result = gpg.encrypt_file(
            f,
            recipients=[recipient_key_id],
            output=output_path,
            always_trust=always_trust,
            armor=False,  # binary output (smaller files)
        )

    if not result.ok:
        logger.error(f"GPG encryption failed: {result.status} - {result.stderr}")
        return False

    logger.info(f"Encrypted {input_path} -> {output_path} for key {recipient_key_id}")
    return True


def decrypt_file(
    input_path: str,
    output_path: str,
    passphrase: Optional[str] = None,
    gpg: Optional[gnupg.GPG] = None,
) -> bool:
    """
    Decrypt a .pgp file using the pipeline's private key.

    Args:
        input_path: Path to the encrypted .pgp file
        output_path: Path where the decrypted plaintext file will be written
        passphrase: Passphrase for the private key (None if no passphrase)
        gpg: Optional GPG client (created fresh if not provided)

    Returns:
        True on success, False on failure
    """
    gpg = gpg or get_gpg_client()

    if not Path(input_path).exists():
        logger.error(f"Input file not found: {input_path}")
        return False

    with open(input_path, "rb") as f:
        result = gpg.decrypt_file(
            f,
            output=output_path,
            passphrase=passphrase,
        )

    if not result.ok:
        logger.error(f"GPG decryption failed: {result.status} - {result.stderr}")
        return False

    logger.info(f"Decrypted {input_path} -> {output_path}")
    return True


def verify_key_present(key_id: str, gpg: Optional[gnupg.GPG] = None) -> bool:
    """Check that the specified key ID is in the local keyring."""
    gpg = gpg or get_gpg_client()
    keys = gpg.list_keys()
    return any(key_id.upper() in k["keyid"].upper() for k in keys)
