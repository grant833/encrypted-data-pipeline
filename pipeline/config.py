"""
Centralized configuration loading.

Loads credentials and settings from environment variables (via .env file).
Never hardcode secrets — always read from env.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class AWSConfig:
    access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    inbound_bucket: str = os.getenv("S3_INBOUND_BUCKET", "")
    outbound_bucket: str = os.getenv("S3_OUTBOUND_BUCKET", "")
    archive_bucket: str = os.getenv("S3_ARCHIVE_BUCKET", "")


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str = os.getenv("SNOWFLAKE_ACCOUNT", "")
    user: str = os.getenv("SNOWFLAKE_USER", "")
    password: str = os.getenv("SNOWFLAKE_PASSWORD", "")
    warehouse: str = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    database: str = os.getenv("SNOWFLAKE_DATABASE", "PIPELINE_PROJECT")
    schema: str = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    role: str = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")

    def connection_params(self) -> dict:
        """Return dict suitable for snowflake.connector.connect()."""
        return {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
            "role": self.role,
        }


@dataclass(frozen=True)
class PostgresConfig:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "pipeline_db")
    user: str = os.getenv("POSTGRES_USER", "pipeline_user")
    password: str = os.getenv("POSTGRES_PASSWORD", "")

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class GPGConfig:
    inbound_key_id: str = os.getenv("GPG_INBOUND_KEY_ID", "")
    vendor_key_id: str = os.getenv("GPG_VENDOR_KEY_ID", "")
    passphrase: str = os.getenv("GPG_PASSPHRASE", "")


@dataclass(frozen=True)
class SlackConfig:
    bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    alert_channel: str = os.getenv("SLACK_ALERT_CHANNEL", "#pipeline-alerts")


# Singleton instances
aws_config = AWSConfig()
snowflake_config = SnowflakeConfig()
postgres_config = PostgresConfig()
gpg_config = GPGConfig()
slack_config = SlackConfig()
