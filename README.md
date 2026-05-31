# Northstar Encrypted Data Pipeline

An end-to-end PGP-encrypted data pipeline running 24/7 on a Raspberry Pi 5, modeled after enterprise consumer-finance data infrastructure. Encrypted files flow from S3 inbound buckets through eight processing stages — decryption, validation, privacy suppression, identity resolution, warehouse load, and audit — with delivery confirmations encrypted and pushed back to S3 outbound. The pipeline is orchestrated by Apache Airflow on a daily schedule, with live operational metrics on a Streamlit dashboard and success/failure pings to Slack.

> All records are synthetically generated using the `faker` library. No real PII anywhere. "Northstar Financial" is a fictional company that does not exist.

## What it does

A file arrives encrypted as a `.pgp` in the S3 inbound bucket. Airflow's scheduler triggers the DAG (daily at 3am UTC, or manually). The pipeline downloads the file, decrypts it with the inbound private key, parses it into a pandas dataframe, and runs it through nine orchestrated tasks: validation against reject rules, suppression against privacy and fraud watchlists, identity resolution via SHA-256 hash matching, bulk-load to a PostgreSQL warehouse, and a battery of audit queries. A delivery summary is built, encrypted with the vendor's public key, and uploaded to the outbound S3 bucket. A formatted success or failure message is posted to Slack. The Streamlit dashboard reads from the audit log every 30 seconds and renders live metrics.

## Tech stack

Python 3.13 · PostgreSQL 17 · Apache Airflow 2.11 · GPG/PGP · AWS S3 (boto3) · Slack SDK · Streamlit · Plotly · pandas · SQLAlchemy · pytest · systemd

Running on a Raspberry Pi 5 (8GB) in Atlanta, Georgia. All services managed by systemd — survives reboots, auto-restarts on crash.

## Architecture

See `docs/architecture.pdf` for the full system diagram and per-task breakdown.

The pipeline lives on a single Raspberry Pi 5 running Postgres, Airflow (scheduler + webserver), and Streamlit as systemd services. External integrations: AWS S3 for inbound/outbound file transfer, Slack for operational alerting, GPG for end-to-end encryption.

## Project structure

- dags/ — Airflow DAG (customer_application_pipeline)
- pipeline/ — Core modules:
  - encryption.py — GPG decrypt/encrypt wrappers
  - reject_rules.py — validation rules engine
  - suppression_engine.py — privacy + fraud filtering
  - identity_resolution.py — SHA-256 hash matching
  - loader.py — Postgres bulk insert
  - audit.py — post-load audit queries + volume anomaly detection
  - alerting.py — Slack success/failure messages
  - s3_utils.py — S3 upload/download helpers
- sql/ — schema.sql + audit_queries.sql + seed data
- dashboard/ — Streamlit live monitoring dashboard
- data_gen/ — Synthetic data generator + S3 upload script
- tests/ — 45+ pytest unit tests
- ops/systemd/ — systemd service files for reproducibility
- docs/ — architecture PDF + screenshots

## Pipeline DAG (9 tasks)

initialize_run → ingest_file → apply_reject_rules → apply_suppression → resolve_identities → load_to_warehouse → run_post_load_audit → encrypt_outbound → send_completion_alert

Each task writes its output to a temp parquet file and passes the path via XCom — avoids serializing large dataframes through Airflow's metadata database.

## Build status

- [x] Phase 0 — Raspberry Pi 5 setup
- [x] Phase 1 — Software stack (Python, Postgres, Airflow, Git, GPG)
- [x] Phase 2 — AWS S3 (real inbound and outbound buckets)
- [x] Phase 3 — GPG encryption (end-to-end, two key pairs)
- [x] Phase 4 — Synthetic data generator (50K records per file via faker)
- [x] Phase 5 — PostgreSQL schema (8 tables, seeded suppression data)
- [x] Phase 6 — Reject rules engine (9 rules, 9 passing tests)
- [x] Phase 7 — Suppression engine (8 passing tests)
- [x] Phase 8 — Identity resolution (SHA-256 hash matching, 14 passing tests)
- [x] Phase 9 — Warehouse loader (SQLAlchemy Core bulk insert, 6 passing tests)
- [x] Phase 10 — Audit layer (stage-level logging + volume anomaly detection, 8 passing tests)
- [x] Phase 11 — Airflow orchestration (TaskFlow API, systemd-managed)
- [x] Phase 12 — Streamlit dashboard (live metrics, systemd-managed)
- [x] Phase 13 — Slack alerts (success + failure callbacks)
- [ ] Phase 14 — Docker (deferred)
- [x] Phase 15 — Architecture documentation + README

## Running it

This pipeline is built to run on a specific Pi setup. The Pi runs four services (Postgres, Airflow scheduler, Airflow webserver, Streamlit) as systemd units. To reproduce the environment on another Pi or Linux box:

1. Clone the repo, create a Python venv, pip install -r requirements.txt
2. Install PostgreSQL 17, create pipeline_db and airflow_db databases
3. Load the schema: psql -d pipeline_db -f sql/schema.sql
4. Set up GPG keys for inbound and vendor identities (see docs/architecture.pdf)
5. Create S3 buckets and IAM user
6. Copy .env.example to .env and fill in your credentials
7. Initialize Airflow: airflow db migrate, then airflow users create ...
8. Install systemd units from ops/systemd/
9. Trigger the DAG: airflow dags trigger customer_application_pipeline

## Tests

pytest tests/ -v

45+ tests across reject rules, suppression, identity resolution, loader, and audit modules. All pass.

## Author

Grant Shimer
