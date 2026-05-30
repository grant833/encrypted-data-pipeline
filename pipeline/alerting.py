"""
Slack alerting for pipeline events.

Posts formatted messages to Slack on pipeline success, failure, and other
events. Integrates with Airflow's on_failure_callback hook for automatic
failure notifications.
"""

import logging
import os
from typing import Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def _get_slack_client() -> Optional[WebClient]:
    """Build a Slack client from environment. Returns None if no token configured."""
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set; Slack alerts disabled")
        return None
    return WebClient(token=token)


def _get_channel() -> str:
    """Return the configured alert channel, defaulting if not set."""
    return os.getenv("SLACK_ALERT_CHANNEL", "all-encrypted-data-pipeline-monitor")


def send_success_alert(
    feed_name: str,
    pipeline_run_id: str,
    record_count: int,
    rejected_count: int = 0,
    suppressed_count: int = 0,
    runtime_seconds: Optional[float] = None,
    channel: Optional[str] = None,
) -> bool:
    """
    Post a formatted success message to Slack.

    Args:
        feed_name: Name of the feed processed
        pipeline_run_id: Unique run identifier
        record_count: Records loaded to warehouse
        rejected_count: Records rejected by validation
        suppressed_count: Records excluded by suppression
        runtime_seconds: Total pipeline runtime
        channel: Override channel (defaults to env config)

    Returns:
        True if message posted, False otherwise
    """
    client = _get_slack_client()
    if not client:
        return False

    target_channel = channel or _get_channel()
    runtime_str = f"{runtime_seconds:.1f}s" if runtime_seconds else "n/a"

    text = (
        f":white_check_mark: *Pipeline Run Complete*\n"
        f"*Feed:* `{feed_name}`\n"
        f"*Run ID:* `{pipeline_run_id}`\n"
        f"*Records Loaded:* {record_count:,}\n"
        f"*Rejected:* {rejected_count:,}\n"
        f"*Suppressed:* {suppressed_count:,}\n"
        f"*Runtime:* {runtime_str}"
    )

    try:
        client.chat_postMessage(channel=target_channel, text=text)
        logger.info(f"Sent success alert to Slack for run {pipeline_run_id}")
        return True
    except SlackApiError as e:
        logger.error(f"Slack alert failed: {e.response.get('error')}")
        return False


def send_failure_alert(
    feed_name: str,
    pipeline_run_id: str,
    failed_task: str,
    error_message: str,
    channel: Optional[str] = None,
) -> bool:
    """
    Post a formatted failure message to Slack.

    Args:
        feed_name: Name of the feed being processed
        pipeline_run_id: Unique run identifier
        failed_task: Name of the task that failed
        error_message: Error details (truncated if very long)
        channel: Override channel (defaults to env config)

    Returns:
        True if message posted, False otherwise
    """
    client = _get_slack_client()
    if not client:
        return False

    target_channel = channel or _get_channel()
    # Truncate very long errors
    err = error_message[:500] + ("..." if len(error_message) > 500 else "")

    text = (
        f":rotating_light: *Pipeline Run FAILED*\n"
        f"*Feed:* `{feed_name}`\n"
        f"*Run ID:* `{pipeline_run_id}`\n"
        f"*Failed Task:* `{failed_task}`\n"
        f"*Error:*\n```{err}```"
    )

    try:
        client.chat_postMessage(channel=target_channel, text=text)
        logger.info(f"Sent failure alert to Slack for run {pipeline_run_id}")
        return True
    except SlackApiError as e:
        logger.error(f"Slack alert failed: {e.response.get('error')}")
        return False


def airflow_failure_callback(context: dict) -> None:
    """
    Callback function for Airflow's on_failure_callback hook.

    Called automatically by Airflow when any task fails. Extracts task
    details from the context and sends a Slack failure alert.

    Args:
        context: Airflow task context dict with task_instance, exception, etc.
    """
    try:
        task_instance = context.get("task_instance")
        exception = context.get("exception", "Unknown error")
        dag_run = context.get("dag_run")

        feed_name = "customer_applications"
        failed_task = task_instance.task_id if task_instance else "unknown"
        run_id = dag_run.run_id if dag_run else "unknown"

        send_failure_alert(
            feed_name=feed_name,
            pipeline_run_id=run_id,
            failed_task=failed_task,
            error_message=str(exception),
        )
    except Exception as e:
        # Never let the callback itself crash the pipeline
        logger.error(f"Failure callback errored: {e}")
