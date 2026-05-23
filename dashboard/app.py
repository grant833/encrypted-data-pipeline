"""
Pipeline Monitoring Dashboard.

Live Streamlit dashboard pulling from pipeline_audit_log to surface:
  - Pipeline health metrics (run counts, success rate)
  - Volume trends over time
  - Reject rates by reason
  - Suppression rates by source
  - Identity match rates
  - Recent run history

Access at http://[pi-ip]:8501 after running:
    streamlit run dashboard/app.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine


# ===== Page Config =====
st.set_page_config(
    page_title="Pipeline Monitor",
    page_icon="📊",
    layout="wide",
)


# ===== Database Connection =====
@st.cache_resource
def get_engine():
    """Create SQLAlchemy engine from env variables."""
    user = os.getenv("POSTGRES_USER", "pipeline_user")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "pipeline_db")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


engine = get_engine()


# ===== Header =====
st.title("📊 Data Pipeline Monitor")
st.caption("Real-time monitoring of the encrypted data pipeline running on Raspberry Pi")


# ===== Top-Line Metrics =====
col1, col2, col3, col4 = st.columns(4)

# TODO: Replace placeholder values with actual queries
with col1:
    st.metric("Total Pipeline Runs", "—")
with col2:
    st.metric("Successful Runs", "—")
with col3:
    st.metric("Failed Runs", "—")
with col4:
    st.metric("Total Records Processed", "—")


# ===== Volume Trend =====
st.subheader("Daily Record Volume by Feed")
# TODO: Query pipeline_audit_log grouped by date and feed_name
# TODO: Plot with plotly express line chart
st.info("Volume chart will appear here once pipeline has run data")


# ===== Reject Rates =====
col1, col2 = st.columns(2)

with col1:
    st.subheader("Reject Rates by Reason")
    # TODO: Query rejected_records grouped by reject_reason
    # TODO: Plot as bar chart

with col2:
    st.subheader("Suppression Rates by Source")
    # TODO: Query suppression_exclusions grouped by suppression_source
    # TODO: Plot as bar chart


# ===== Identity Match Rate =====
st.subheader("Identity Resolution Match Rates")
# TODO: Query identity match rate by run, plot over time


# ===== Recent Runs =====
st.subheader("Recent Pipeline Runs")
# TODO: SELECT last 20 rows from pipeline_audit_log


# ===== Footer =====
st.caption("All data is synthetically generated. No real PII is processed.")
