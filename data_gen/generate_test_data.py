"""
Synthetic data generator for the encrypted data pipeline project.

Generates fake customer application data for a fictional consumer finance
company ("Northstar Financial"). No real PII anywhere — all data produced
by the faker library.

Usage:
    python data_gen/generate_test_data.py --records 50000 --output ./data/
"""

import argparse
import random
import string
from datetime import datetime
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)


def generate_application_id() -> str:
    """Generate a customer application ID."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=14))
    return f"APP-{suffix}"


def generate_customer_id() -> str:
    """Generate a customer account ID."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=17))
    return f"CUST-{suffix}"


def generate_application_record() -> dict:
    """Generate a single fake customer application record."""
    first = fake.first_name()
    last = fake.last_name()
    return {
        "first_name": first,
        "middle_initial": random.choice(string.ascii_uppercase),
        "last_name": last,
        "street_address": fake.street_address()[:100],
        "city": fake.city()[:20],
        "state": fake.state_abbr(),
        "zip_code": fake.zipcode()[:5],
        "application_id": generate_application_id(),
        "customer_id": generate_customer_id(),
        "division_id": random.randint(100, 999),
        "submitted_date": fake.date_between(start_date="-1y", end_date="today").isoformat(),
        "application_status": random.choices(["approved", "declined", "under_review"], weights=[70, 20, 10])[0],
        "email_address": f"{first.lower()}.{last.lower()}@{fake.free_email_domain()}"[:80],
        "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=85).isoformat(),
    }


def generate_application_file(num_records: int = 10000) -> pd.DataFrame:
    """Generate a full customer application file."""
    records = [generate_application_record() for _ in range(num_records)]
    return pd.DataFrame(records)


def generate_suppression_file(num_records: int = 500) -> pd.DataFrame:
    """Generate a privacy suppression file (CCPA opt-outs and deletes)."""
    records = []
    for i in range(num_records):
        first = fake.first_name()
        last = fake.last_name()
        records.append({
            "case_number": f"PRIV-{str(i).zfill(8)}",
            "email_address": f"{first.lower()}.{last.lower()}@{fake.free_email_domain()}",
            "first_name": first,
            "last_name": last,
            "request_type": random.choice(["opt_out", "delete"]),
        })
    return pd.DataFrame(records)


def generate_fraud_list_file(num_records: int = 100) -> pd.DataFrame:
    """Generate a fraud watchlist file."""
    records = []
    for _ in range(num_records):
        records.append({
            "application_id": generate_application_id(),
            "flag_reason": random.choice([
                "fraudulent_application",
                "repeated_declines",
                "identity_theft_flag",
                "synthetic_identity",
            ]),
        })
    return pd.DataFrame(records)


def inject_bad_records(df: pd.DataFrame, bad_pct: float = 0.03) -> pd.DataFrame:
    """Inject intentionally bad records to test the reject rules engine."""
    num_bad = int(len(df) * bad_pct)
    bad_indices = random.sample(range(len(df)), num_bad)

    for i, idx in enumerate(bad_indices):
        mutation = i % 4
        if mutation == 0:
            df.at[idx, "application_id"] = ""
        elif mutation == 1:
            df.at[idx, "application_status"] = "INVALID_STATUS"
        elif mutation == 2:
            df.at[idx, "state"] = "GEORGIA"
        elif mutation == 3:
            df.at[idx, "zip_code"] = "ABCDE"

    return df


def write_pipe_delimited(df: pd.DataFrame, output_path: str) -> None:
    df.to_csv(output_path, sep="|", index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=10000)
    parser.add_argument("--output", type=str, default="./data/")
    parser.add_argument("--inject-bad", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")

    print(f"Generating {args.records:,} customer application records...")
    app_df = generate_application_file(args.records)
    if args.inject_bad:
        print("Injecting 3% intentionally bad records...")
        app_df = inject_bad_records(app_df)
    app_path = output_dir / f"customer_applications_{timestamp}.txt"
    write_pipe_delimited(app_df, str(app_path))
    print(f"  -> {app_path}")

    print("\nGenerating privacy suppression file (500 records)...")
    supp_df = generate_suppression_file(500)
    supp_path = output_dir / f"privacy_suppressions_{timestamp}.csv"
    supp_df.to_csv(supp_path, index=False)
    print(f"  -> {supp_path}")

    print("\nGenerating fraud watchlist file (100 records)...")
    fraud_df = generate_fraud_list_file(100)
    fraud_path = output_dir / f"fraud_watchlist_{timestamp}.csv"
    fraud_df.to_csv(fraud_path, index=False)
    print(f"  -> {fraud_path}")

    print(f"\nDone. All files written to {output_dir}/")


if __name__ == "__main__":
    main()
