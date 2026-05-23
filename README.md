# Encrypted Data Pipeline Project

End-to-end encrypted data pipeline running on a Raspberry Pi, modeled after enterprise financial data infrastructure. Handles encrypted file ingestion, schema validation, suppression logic, identity resolution, multi-warehouse loading, and audit reporting — fully orchestrated and monitored.

> **All data in this project is synthetically generated using the `faker` library. No real PII is used anywhere.**

---

## Architecture

```
INBOUND ZONE          PROCESSING ZONE              OUTBOUND ZONE

S3 Inbound Bucket --> Pi Watcher --> Decrypt GPG --> Reject Rules
                                          |
                              Schema Validation
                                          |
                              Suppression Engine <-- Suppression Tables
                                          |
                              Identity Resolution
                                          |
                    Local PostgreSQL <-- Load Clean Records --> Snowflake
                                          |
                              Audit SQL Queries
                                          |
                              Re-encrypt Output --> S3 Outbound Bucket
                                          |
                         Streamlit Dashboard + Slack Alerts
```

A full architecture diagram lives in `docs/architecture.png`.

---

## Tech Stack

- **Language:** Python 3.11
- **Orchestration:** Apache Airflow
- **Local Warehouse:** PostgreSQL 15
- **Cloud Warehouse:** Snowflake
- **Object Storage:** AWS S3
- **Encryption:** GPG (python-gnupg)
- **Data Validation:** Great Expectations + custom reject rules engine
- **Identity Matching:** recordlinkage
- **Dashboard:** Streamlit + Plotly
- **Alerting:** Slack SDK + SendGrid (backup email)
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Hardware:** Raspberry Pi 5 (8GB)

---

## Project Structure

```
pipeline-project/
├── dags/                       # Airflow DAGs
│   └── application_pipeline.py
├── pipeline/                   # Core pipeline modules
│   ├── encryption.py           # GPG encrypt/decrypt
│   ├── reject_rules.py         # Validation engine
│   ├── suppression_engine.py   # Suppression matching
│   ├── identity_resolution.py  # Identity dedup
│   ├── loader.py               # Postgres + Snowflake loading
│   ├── audit.py                # SQL audit wrapper
│   ├── alerting.py             # Slack notifications
│   ├── config.py               # Config loading
│   └── s3_utils.py             # S3 helpers
├── sql/                        # SQL files
│   ├── schema.sql              # Warehouse schema
│   ├── audit_queries.sql       # Audit query definitions
│   └── seed_suppression_data.sql
├── dashboard/                  # Streamlit dashboard
│   └── app.py
├── data_gen/                   # Synthetic data generation
│   ├── generate_test_data.py
│   └── upload_to_s3.py
├── tests/                      # Unit tests
├── docs/                       # Architecture diagrams, screenshots
├── docker-compose.yml          # Container orchestration
├── requirements.txt            # Python dependencies
├── .env.example                # Credentials template
└── README.md
```

---

## Setup

### Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS Lite 64-bit installed
- AWS account with S3 buckets created
- Snowflake trial account
- Slack workspace with bot token

### Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/[username]/pipeline-project.git
   cd pipeline-project
   ```

2. Create Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Generate GPG keys:
   ```bash
   gpg --full-generate-key  # Run twice — once for "Acxiom" key, once for "vendor" key
   ```

4. Copy environment variables and fill in credentials:
   ```bash
   cp .env.example .env
   # Edit .env with AWS, Snowflake, and Slack credentials
   ```

5. Initialize Postgres schema:
   ```bash
   psql -U postgres -f sql/schema.sql
   ```

6. Generate synthetic test data:
   ```bash
   python data_gen/generate_test_data.py
   python data_gen/upload_to_s3.py
   ```

7. Start the pipeline:
   ```bash
   docker compose up -d
   ```

8. Access services:
   - Airflow UI: `http://[pi-ip]:8080`
   - Streamlit dashboard: `http://[pi-ip]:8501`

---

## How It Works

A file arrives encrypted in the S3 inbound bucket. Airflow detects it, decrypts it with the private GPG key, and loads it as a pandas dataframe. The reject rules engine splits records into clean and rejected groups based on configurable validation rules. Clean records pass through the suppression engine, which checks each against CCPA opt-out and credit abuser tables. Surviving records go through identity resolution — either matched to an existing identity or assigned a new one. Resolved records load to both Postgres and Snowflake. Audit SQL runs after load to verify counts, suppression rates, and identity match rates. The pipeline re-encrypts an outbound file with the vendor's public key and writes it to the outbound S3 bucket. Slack fires a completion alert. Total runtime for a 100K-record file: ~5 minutes.

---

## Status

Build phase tracker (see `docs/phases.md` for full breakdown):

- [ ] Phase 0 — Pi setup
- [ ] Phase 1 — Software stack
- [ ] Phase 2 — Cloud accounts + S3
- [ ] Phase 3 — GPG keys
- [ ] Phase 4 — Synthetic data generator
- [ ] Phase 5 — Postgres schema
- [ ] Phase 6 — Reject rules engine
- [ ] Phase 7 — Suppression engine
- [ ] Phase 8 — Identity resolution
- [ ] Phase 9 — Warehouse loader
- [ ] Phase 10 — SQL audit layer
- [ ] Phase 11 — Airflow DAG wiring
- [ ] Phase 12 — Streamlit dashboard
- [ ] Phase 13 — Slack alerting
- [ ] Phase 14 — Dockerize + document
- [ ] Phase 15 — Polish and post

---

## License

MIT
