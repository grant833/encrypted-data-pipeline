"""
Pre-process reject rules engine.

Validates every record in an incoming file against configurable rules
before any downstream processing. Splits records into passed and rejected
groups, with reject reasons attached.

Rule types:
    - required: field must not be null or empty
    - max_length: field value length must not exceed N
    - min_length: field value length must be at least N
    - valid_values: field value must be in an allowed set
    - format: field value must match a regex pattern
    - numeric_range: numeric field must fall within [min, max]
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RejectRule:
    """Defines a single validation rule applied to a specific field."""

    field: str
    rule_type: str
    parameter: Any = None
    description: str = ""


class RejectThresholdExceededError(Exception):
    """Raised when the reject rate exceeds the configured threshold."""
    pass


class PreProcessRejectEngine:
    """
    Applies a list of reject rules to an incoming dataframe and splits
    records into passed and rejected groups.

    If reject rate exceeds threshold, raises RejectThresholdExceededError
    to halt the pipeline.
    """

    def __init__(self, rules: List[RejectRule], reject_threshold: float = 0.05):
        self.rules = rules
        self.reject_threshold = reject_threshold

    def apply_rules(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply all rules and split the dataframe into passed and rejected.

        Returns:
            (passed_df, rejected_df) - rejected_df has a 'reject_reason' column
        """
        if df.empty:
            logger.warning("Empty dataframe passed to reject engine")
            return df.copy(), df.copy()

        df = df.copy()
        df["reject_reason"] = None

        for rule in self.rules:
            if rule.field not in df.columns:
                logger.warning(f"Field '{rule.field}' not in dataframe, skipping rule")
                continue

            mask = self._get_failure_mask(df, rule)

            # Only flag records that haven't already been flagged
            new_failures = mask & df["reject_reason"].isna()
            df.loc[new_failures, "reject_reason"] = rule.description or f"Failed {rule.rule_type} on {rule.field}"

        passed = df[df["reject_reason"].isna()].drop(columns=["reject_reason"]).copy()
        rejected = df[df["reject_reason"].notna()].copy()

        reject_rate = len(rejected) / len(df) if len(df) > 0 else 0
        logger.info(
            f"Reject engine processed {len(df):,} records: "
            f"{len(passed):,} passed, {len(rejected):,} rejected ({reject_rate:.2%})"
        )

        if reject_rate > self.reject_threshold:
            raise RejectThresholdExceededError(
                f"Reject rate {reject_rate:.2%} exceeds threshold {self.reject_threshold:.2%}"
            )

        return passed, rejected

    def _get_failure_mask(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Return a boolean mask of records that fail this rule."""
        if rule.rule_type == "required":
            return self._apply_required(df, rule)
        elif rule.rule_type == "max_length":
            return self._apply_max_length(df, rule)
        elif rule.rule_type == "min_length":
            return self._apply_min_length(df, rule)
        elif rule.rule_type == "valid_values":
            return self._apply_valid_values(df, rule)
        elif rule.rule_type == "format":
            return self._apply_format(df, rule)
        elif rule.rule_type == "numeric_range":
            return self._apply_numeric_range(df, rule)
        else:
            logger.warning(f"Unknown rule type: {rule.rule_type}")
            return pd.Series([False] * len(df), index=df.index)

    def _apply_required(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Fail records where field is null or empty string."""
        return df[rule.field].isna() | (df[rule.field].astype(str).str.strip() == "")

    def _apply_max_length(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Fail records where field length exceeds the limit."""
        return df[rule.field].astype(str).str.len() > rule.parameter

    def _apply_min_length(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Fail records where field length is below the minimum."""
        return df[rule.field].astype(str).str.len() < rule.parameter

    def _apply_valid_values(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Fail records where field is not in the allowed set."""
        return ~df[rule.field].isin(rule.parameter)

    def _apply_format(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Fail records where field does not match the regex pattern."""
        pattern = re.compile(rule.parameter)
        return ~df[rule.field].astype(str).apply(lambda x: bool(pattern.match(x)))

    def _apply_numeric_range(self, df: pd.DataFrame, rule: RejectRule) -> pd.Series:
        """Fail records where numeric field is outside [min, max]."""
        min_val, max_val = rule.parameter
        numeric = pd.to_numeric(df[rule.field], errors="coerce")
        return numeric.isna() | (numeric < min_val) | (numeric > max_val)


# ===== Predefined rule sets =====

CUSTOMER_APPLICATION_RULES: List[RejectRule] = [
    RejectRule("application_id", "required", None, "application_id cannot be null"),
    RejectRule("application_status", "valid_values",
               ["approved", "declined", "under_review"],
               "Invalid application_status"),
    RejectRule("state", "max_length", 2, "state must be 2 characters"),
    RejectRule("zip_code", "format", r"^\d{5}$", "zip_code must be 5 digits"),
    RejectRule("email_address", "max_length", 80, "email_address exceeds max length"),
    RejectRule("first_name", "required", None, "first_name cannot be null"),
    RejectRule("last_name", "required", None, "last_name cannot be null"),
]
