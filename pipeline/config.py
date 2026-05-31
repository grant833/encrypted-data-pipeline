"""
Centralized configuration loaded from environment variables.

Reads from .env via python-dotenv. All sensitive values come from the
environment — nothing is hardcoded in this module.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PostgresConfig:
    """PostgreSQL connection settings."""
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


@dataclass
class S3Config:
    """AWS S3 bucket settings."""
    inbound_bucket: str = os.getenv("S3_INBOUND_BUCKET", "")
    outbound_bucket: str = os.getenv("S3_OUTBOUND_BUCKET", "")
    region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")


@dataclass
class GPGConfig:
    """GPG encryption settings."""
    inbound_key_id: str = os.getenv("GPG_INBOUND_KEY_ID", "")
    vendor_key_id: str = os.getenv("GPG_VENDOR_KEY_ID", "")


@dataclass
class SlackConfig:
    """Slack alerting settings."""
    bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    alert_channel: str = os.getenv("SLACK_ALERT_CHANNEL", "")


# Convenience singletons
postgres_config = PostgresConfig()
s3_config = S3Config()
gpg_config = GPGConfig()
slack_config = SlackConfig()
