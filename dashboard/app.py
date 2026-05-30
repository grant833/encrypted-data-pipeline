"""
Pipeline Monitoring Dashboard.

Live Streamlit dashboard pulling from pipeline_audit_log and the warehouse
tables. Shows pipeline health, volume trends, stage performance, suppression
rates, and recent run history.

Access at http://[pi-ip]:8501 after running:
    streamlit run dashboard/app.py
"""

import os
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text


# ===== Page Config =====
st.set_page_config(
    page_title="Pipeline Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ===== Database Connection =====
@st.cache_resource
def get_engine():
    """Create SQLAlchemy engine from environment or defaults."""
    user = os.getenv("POSTGRES_USER", "pipeline_user")
    password = os.getenv("POSTGRES_PASSWORD", "Tesla2345!")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "pipeline_db")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


engine = get_engine()


def query_df(sql: str, params: dict = None) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Avoids pandas.read_sql compat issues."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        rows = result.fetchall()
        columns = list(result.keys())
    return pd.DataFrame(rows, columns=columns)


# ===== Header =====
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("📊 Encrypted Data Pipeline Monitor")
    st.caption(
        "Live monitoring of customer application pipeline runs · "
        "Northstar Financial · Running on Raspberry Pi 5"
    )
with col_refresh:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

st.divider()


# ===== Top-Line Metric Cards =====
@st.cache_data(ttl=30)
def get_top_metrics():
    total_runs = query_df("""
        SELECT COUNT(DISTINCT pipeline_run_id) AS count
        FROM pipeline_audit_log
    """)
    success_runs = query_df("""
        SELECT COUNT(DISTINCT pipeline_run_id) AS count
        FROM pipeline_audit_log
        WHERE pipeline_run_id NOT IN (
            SELECT DISTINCT pipeline_run_id
            FROM pipeline_audit_log
            WHERE status = 'FAILED'
        )
    """)
    total_records = query_df("""
        SELECT COALESCE(SUM(record_count), 0) AS count
        FROM pipeline_audit_log
        WHERE stage = 'load'
    """)
    avg_runtime = query_df("""
        SELECT COALESCE(AVG(runtime_seconds), 0) AS seconds
        FROM pipeline_audit_log
        WHERE stage = 'load' AND status = 'SUCCESS'
    """)
    return {
        "total_runs": int(total_runs["count"].iloc[0]),
        "success_runs": int(success_runs["count"].iloc[0]),
        "total_records": int(total_records["count"].iloc[0]),
        "avg_load_runtime": float(avg_runtime["seconds"].iloc[0]),
    }


metrics = get_top_metrics()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Pipeline Runs", f"{metrics['total_runs']:,}")
with col2:
    success_rate = (
        metrics["success_runs"] / metrics["total_runs"] * 100
        if metrics["total_runs"] > 0 else 0
    )
    st.metric(
        "Success Rate",
        f"{success_rate:.1f}%",
        f"{metrics['success_runs']}/{metrics['total_runs']} runs",
    )
with col3:
    st.metric("Total Records Loaded", f"{metrics['total_records']:,}")
with col4:
    st.metric("Avg Load Runtime", f"{metrics['avg_load_runtime']:.1f}s")

st.divider()


# ===== Volume Trend Chart =====
st.subheader("📈 Pipeline Volume Over Time")

@st.cache_data(ttl=30)
def get_volume_data():
    return query_df("""
        SELECT
            DATE_TRUNC('hour', run_timestamp) AS hour,
            SUM(record_count) AS records_loaded
        FROM pipeline_audit_log
        WHERE stage = 'load' AND status = 'SUCCESS'
        GROUP BY hour
        ORDER BY hour
    """)


volume_df = get_volume_data()
if not volume_df.empty:
    fig = px.line(
        volume_df,
        x="hour",
        y="records_loaded",
        title=None,
        markers=True,
    )
    fig.update_layout(
        xaxis_title="Run Time (hour)",
        yaxis_title="Records Loaded",
        height=350,
        margin=dict(l=0, r=0, t=20, b=0),
    )
    fig.update_traces(line_color="#1f77b4", marker=dict(size=8))
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No load data yet. Trigger a pipeline run to populate this chart.")

st.divider()


# ===== Stage Performance =====
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("⏱️ Average Runtime by Stage")

    @st.cache_data(ttl=30)
    def get_stage_runtime():
        return query_df("""
            SELECT
                stage,
                AVG(runtime_seconds) AS avg_seconds,
                COUNT(*) AS run_count
            FROM pipeline_audit_log
            WHERE status = 'SUCCESS' AND runtime_seconds IS NOT NULL
            GROUP BY stage
            ORDER BY avg_seconds DESC
        """)

    stage_df = get_stage_runtime()
    if not stage_df.empty:
        fig = px.bar(
            stage_df,
            x="avg_seconds",
            y="stage",
            orientation="h",
            text="avg_seconds",
        )
        fig.update_traces(
            texttemplate="%{x:.2f}s",
            textposition="outside",
            marker_color="#2ca02c",
        )
        fig.update_layout(
            xaxis_title="Avg Runtime (seconds)",
            yaxis_title=None,
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No stage runtime data yet.")

with col_right:
    st.subheader("📊 Application Status Distribution")

    @st.cache_data(ttl=30)
    def get_status_distribution():
        return query_df("""
            SELECT application_status, COUNT(*) AS count
            FROM customer_applications
            GROUP BY application_status
            ORDER BY count DESC
        """)

    status_df = get_status_distribution()
    if not status_df.empty:
        fig = px.pie(
            status_df,
            values="count",
            names="application_status",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=20, b=0),
            showlegend=True,
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No application data loaded yet.")

st.divider()


# ===== Identity Match Rate =====
st.subheader("🆔 Identity Resolution Match Rate")

@st.cache_data(ttl=30)
def get_match_rate_history():
    return query_df("""
        WITH run_dates AS (
            SELECT
                pipeline_run_id,
                MIN(run_timestamp) AS run_time
            FROM pipeline_audit_log
            WHERE stage = 'load' AND status = 'SUCCESS'
            GROUP BY pipeline_run_id
        ),
        run_identities AS (
            SELECT
                ca.pipeline_run_id,
                COUNT(*) AS total_records,
                SUM(CASE
                    WHEN i.first_seen_timestamp < rd.run_time
                    THEN 1 ELSE 0
                END) AS matched
            FROM customer_applications ca
            JOIN identities i ON ca.identity_id = i.identity_id
            JOIN run_dates rd ON ca.pipeline_run_id = rd.pipeline_run_id
            GROUP BY ca.pipeline_run_id
        )
        SELECT
            ri.pipeline_run_id,
            rd.run_time,
            ri.total_records,
            ri.matched,
            ROUND(ri.matched * 100.0 / NULLIF(ri.total_records, 0), 2) AS match_rate_pct
        FROM run_identities ri
        JOIN run_dates rd ON ri.pipeline_run_id = rd.pipeline_run_id
        ORDER BY rd.run_time
    """)


match_df = get_match_rate_history()
if not match_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=match_df["run_time"],
        y=match_df["match_rate_pct"],
        mode="lines+markers",
        line=dict(color="#ff7f0e", width=2),
        marker=dict(size=10),
        name="Match Rate",
    ))
    fig.update_layout(
        xaxis_title="Run Time",
        yaxis_title="Match Rate (%)",
        yaxis_range=[0, 105],
        height=300,
        margin=dict(l=0, r=0, t=20, b=0),
    )
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Match rate climbs over time as the pipeline encounters returning customers. "
        "The first run on fresh data is 0% (everyone new); subsequent runs approach 100%."
    )
else:
    st.info("No identity resolution data yet.")

st.divider()


# ===== Recent Runs Table =====
st.subheader("🕒 Recent Pipeline Runs")

@st.cache_data(ttl=30)
def get_recent_runs():
    return query_df("""
        SELECT
            pipeline_run_id,
            MIN(run_timestamp) AS run_started,
            COUNT(*) AS stages_completed,
            SUM(record_count) FILTER (WHERE stage = 'load') AS records_loaded,
            SUM(rejected_count) AS total_rejected,
            SUM(suppressed_count) AS total_suppressed,
            ROUND(SUM(runtime_seconds)::numeric, 2) AS total_runtime_sec,
            MAX(CASE WHEN status = 'FAILED' THEN 'FAILED' ELSE 'SUCCESS' END) AS status
        FROM pipeline_audit_log
        GROUP BY pipeline_run_id
        ORDER BY run_started DESC
        LIMIT 20
    """)


recent_df = get_recent_runs()
if not recent_df.empty:
    st.dataframe(
        recent_df,
        width="stretch",
        hide_index=True,
        column_config={
            "pipeline_run_id": "Run ID",
            "run_started": st.column_config.DatetimeColumn(
                "Started", format="MMM D, h:mm a",
            ),
            "stages_completed": "Stages",
            "records_loaded": st.column_config.NumberColumn(
                "Records Loaded", format="%d",
            ),
            "total_rejected": "Rejected",
            "total_suppressed": "Suppressed",
            "total_runtime_sec": st.column_config.NumberColumn(
                "Runtime (s)", format="%.1f",
            ),
            "status": "Status",
        },
    )
else:
    st.info("No pipeline runs recorded yet.")


# ===== Footer =====
st.divider()
st.caption(
    f"Dashboard last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · "
    "All data is synthetically generated · No real PII"
)
