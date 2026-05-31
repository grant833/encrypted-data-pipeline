# Encrypted Data Pipeline

End-to-end encrypted data pipeline running on a Raspberry Pi, modeled after enterprise consumer finance data infrastructure. Handles encrypted file ingestion, schema validation, privacy suppression, identity resolution, multi-warehouse loading, and audit reporting.

> All data is synthetically generated using the faker library. No real PII anywhere. The fictional source company is "Northstar Financial," which does not exist.

## Tech Stack

Python 3.13, Apache Airflow, PostgreSQL 17, Snowflake, AWS S3, GPG, Streamlit, Docker, GitHub Actions. Running on a Raspberry Pi 5 (8GB).

## How It Works

A file arrives encrypted in the S3 inbound bucket. Airflow detects it, decrypts with the private GPG key, and loads it as a pandas dataframe. The reject rules engine splits records into clean and rejected groups. Clean records pass through the suppression engine, which checks each record against privacy opt-out and fraud watchlist tables. Surviving records go through identity resolution. Resolved records load to both Postgres and Snowflake. Audit SQL runs after load to verify counts and surface anomalies. The pipeline re-encrypts an outbound file and writes it to the outbound S3 bucket. Slack fires a completion alert.

## Project Structure

- dags/ - Airflow orchestration
- pipeline/ - Core modules (encryption, reject rules, suppression, identity resolution, loader, audit, alerting)
- sql/ - Schema and audit queries
- dashboard/ - Streamlit monitoring dashboard
- data_gen/ - Synthetic data generator
- tests/ - Unit tests

## Build Status

- [x] Phase 0 - Pi setup
- [x] Phase 1 - Software stack
- [ ] Phase 2 - AWS S3 + cloud accounts
- [ ] Phase 3 - GPG keys
- [x] Phase 4 - Synthetic data generator
- [x] Phase 5 - PostgreSQL schema
- [x] Phase 6 - Reject rules engine
- [ ] Phase 7 - Suppression engine
- [ ] Phase 8 - Identity resolution
- [ ] Phase 9 - Warehouse loader
- [ ] Phase 10 - SQL audit layer
- [ ] Phase 11 - Airflow DAGs
- [ ] Phase 12 - Streamlit dashboard
- [ ] Phase 13 - Slack alerting
- [ ] Phase 14 - Dockerize
- [ ] Phase 15 - Polish and post

## License

MIT
