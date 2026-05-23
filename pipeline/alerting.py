"""
Slack and email alerting for pipeline events.

Posts formatted messages to Slack on success/failure, with email backup
via SendGrid for critical failures.
"""

import logging
import os
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def get_slack_client() -> WebClient:
    """Return a Slack WebClient initialized with bot token from env."""
    # TODO: WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    raise NotImplementedError


def send_success_alert(
    feed_name: str,
    pipeline_run_id: str,
    record_count: int,
    rejected_count: int,
    suppressed_count: int,
    runtime_seconds: float,
    channel: Optional[str] = None,
) -> bool:
    """
    Post a success message to Slack.

    Returns:
        True if message posted, False otherwise
    """
    # TODO: Build formatted message with checkmark emoji and run metrics
    # TODO: Post to channel via client.chat_postMessage
    raise NotImplementedError


def send_failure_alert(
    feed_name: str,
    pipeline_run_id: str,
    failed_task: str,
    error_message: str,
    channel: Optional[str] = None,
) -> bool:
    """
    Post a failure message to Slack with error details.

    Returns:
        True if message posted, False otherwise
    """
    # TODO: Build formatted message with alarm emoji and error info
    # TODO: Post to channel
    raise NotImplementedError


def send_email_alert(
    subject: str,
    body: str,
    to_email: Optional[str] = None,
) -> bool:
    """
    Backup email alert via SendGrid for critical failures.

    Returns:
        True if email sent, False otherwise
    """
    # TODO: Use sendgrid SDK to send email
    raise NotImplementedError


def airflow_failure_callback(context: dict) -> None:
    """
    Callback function for Airflow's on_failure_callback hook.

    Args:
        context: Airflow task context dict (contains 'task_instance', 'exception', etc.)
    """
    # TODO: Extract task name and exception from context
    # TODO: Call send_failure_alert
    raise NotImplementedError
