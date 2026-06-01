"""Tests for the identity resolution layer."""

from pipeline.identity_resolution import (
    normalize_field,
    compute_identity_hash,
)

# ===== normalize_field tests =====


def test_normalize_lowercases():
    assert normalize_field("Grant") == "grant"
    assert normalize_field("SHIMER") == "shimer"


def test_normalize_strips_whitespace():
    assert normalize_field("  grant  ") == "grant"
    assert normalize_field("123 Main St") == "123mainst"


def test_normalize_removes_punctuation():
    assert normalize_field("O'Brien") == "obrien"
    assert normalize_field("123 Main St.") == "123mainst"
    assert normalize_field("Jean-Luc") == "jeanluc"


def test_normalize_handles_none():
    assert normalize_field(None) == ""
    assert normalize_field("") == ""


def test_normalize_keeps_digits():
    assert normalize_field("30309") == "30309"
    assert normalize_field("Apt 4B") == "apt4b"


# ===== compute_identity_hash tests =====


def test_identical_records_produce_same_hash():
    """Two identical records should hash to the same fingerprint."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = r1.copy()
    assert compute_identity_hash(r1) == compute_identity_hash(r2)


def test_different_records_produce_different_hashes():
    """Different identity fields should hash to different fingerprints."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "456 Oak Ave",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    assert compute_identity_hash(r1) != compute_identity_hash(r2)


def test_case_insensitive_matching():
    """Case differences in name fields should not produce different hashes."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = {
        "first_name": "GRANT",
        "last_name": "shimer",
        "street_address": "123 main st",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    assert compute_identity_hash(r1) == compute_identity_hash(r2)


def test_whitespace_doesnt_affect_hash():
    """Extra whitespace should be ignored."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = {
        "first_name": "  Grant  ",
        "last_name": "Shimer  ",
        "street_address": "  123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    assert compute_identity_hash(r1) == compute_identity_hash(r2)


def test_punctuation_doesnt_affect_hash():
    """Punctuation should be normalized away."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St.",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    assert compute_identity_hash(r1) == compute_identity_hash(r2)


def test_only_year_of_birth_matters_not_full_date():
    """Two records with same year but different month/day should match."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-12-15",
    }
    assert compute_identity_hash(r1) == compute_identity_hash(r2)


def test_different_year_produces_different_hash():
    """Different year of birth should produce different hashes."""
    r1 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    r2 = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "1985-04-30",
    }
    assert compute_identity_hash(r1) != compute_identity_hash(r2)


def test_hash_is_sha256_length():
    """Hash should be a 64-character hex SHA-256."""
    r = {
        "first_name": "Grant",
        "last_name": "Shimer",
        "street_address": "123 Main St",
        "zip_code": "30309",
        "date_of_birth": "2005-04-30",
    }
    h = compute_identity_hash(r)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_missing_fields_still_produces_hash():
    """Records with missing fields should still produce a valid hash, not crash."""
    r = {"first_name": "Grant"}
    h = compute_identity_hash(r)
    assert len(h) == 64
