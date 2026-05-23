"""
Synthetic data generator using faker.

Generates realistic-looking but completely fake application files matching
the structure of real Bread Financial feeds. No real PII anywhere.

Usage:
    python data_gen/generate_test_data.py --records 50000 --output ./data/

Outputs:
    - BF_Applications_YYYYMMDD.txt   (pipe-delimited, like real feeds)
    - BF_Suppressions_YYYYMMDD.csv
    - BF_CreditAbusers_YYYYMMDD.csv
"""

import argparse
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)  # Reproducible runs


# Field layout matching the actual Bread application feed
APPLICATION_FIELDS = [
    "First_Name",
    "Middle_Init",
    "Last_Name",
    "Str_Addr",
    "City",
    "State",
    "Zip_Cd",
    "Application_ID",
    "Acct_ID",
    "Div_No",
    "Entry_Date",
    "App_Status_Flag",
    "email_addr",
    "birth_date",
]


def generate_application_record() -> dict:
    """Generate a single fake application record."""
    # TODO: Use fake.first_name(), fake.last_name(), fake.street_address(), etc.
    # TODO: Generate Application_ID with a recognizable prefix (e.g., 'APP-')
    # TODO: Randomize App_Status_Flag among ['A', 'D', 'U']
    raise NotImplementedError


def generate_application_file(num_records: int = 10000) -> pd.DataFrame:
    """Generate a full application file dataframe."""
    # TODO: Loop and build list of records, return as DataFrame
    raise NotImplementedError


def generate_suppression_file(num_records: int = 500) -> pd.DataFrame:
    """Generate a CCPA suppression file."""
    # TODO: Generate records with casenumber, email, name fields
    raise NotImplementedError


def generate_credit_abuser_file(num_records: int = 100) -> pd.DataFrame:
    """Generate a credit abuser file."""
    # TODO: Generate records with application_id and flagged_reason
    raise NotImplementedError


def inject_bad_records(df: pd.DataFrame, bad_pct: float = 0.03) -> pd.DataFrame:
    """
    Inject intentionally bad records to test the reject rules engine.

    Mutations to add:
        - Null Application_IDs
        - Invalid status flags (e.g., 'X' instead of A/D/U)
        - Over-length state codes
        - Malformed zip codes
        - Over-length email addresses
    """
    # TODO: Sample bad_pct of records and mutate them
    raise NotImplementedError


def write_pipe_delimited(df: pd.DataFrame, output_path: str) -> None:
    """Write dataframe as pipe-delimited file (matches real feed format)."""
    df.to_csv(output_path, sep="|", index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=10000)
    parser.add_argument("--output", type=str, default="./data/")
    parser.add_argument("--inject-bad", action="store_true",
                        help="Inject 3% bad records for reject rule testing")
    args = parser.parse_args()

    Path(args.output).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")

    # TODO: Generate application file
    # TODO: Optionally inject bad records
    # TODO: Write pipe-delimited file to output dir
    # TODO: Generate suppression and credit abuser files

    print(f"Generated {args.records} records to {args.output}")


if __name__ == "__main__":
    main()
