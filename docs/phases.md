# Build Phases

Detailed phase-by-phase build plan. Check off as you go.

---

## Phase 0 — Pi Setup (~2 hours)
- [ ] Assemble case, install fan and heatsink, seat Pi
- [ ] Flash Raspberry Pi OS Lite 64-bit (configure hostname, SSH, WiFi in Imager)
- [ ] Boot Pi, SSH in from laptop
- [ ] Run `sudo apt update && sudo apt full-upgrade -y`
- [ ] Set static IP reservation in router
- [ ] Verify SSH works at static IP

**Deliverable:** SSH into Pi from laptop, see `htop` output.

---

## Phase 1 — Software Stack (~3 hours)
- [ ] Install Python 3.11, pip, venv
- [ ] Install PostgreSQL 15
- [ ] Install Docker + Docker Compose
- [ ] Install Git, GPG (verify pre-installed)
- [ ] Create Python venv, `pip install -r requirements.txt`
- [ ] Create Postgres user and database
- [ ] Test each tool with hello-world

**Deliverable:** Every dependency installed and responding.

---

## Phase 2 — Cloud Accounts + S3 (~2 hours)
- [ ] Create AWS account, set up IAM user with S3-only access
- [ ] Configure AWS CLI on Pi with credentials
- [ ] Create three S3 buckets (inbound, outbound, archive)
- [ ] Test upload/download via boto3
- [ ] Sign up for Snowflake trial
- [ ] Create database, schema, user
- [ ] Test connection from Python script (`SELECT 1`)

**Deliverable:** Pi can talk to S3 and Snowflake.

---

## Phase 3 — GPG Keys (~1 hour)
- [ ] Generate "Acxiom" inbound key pair (`gpg --full-generate-key`)
- [ ] Generate "vendor" key pair
- [ ] Export public keys
- [ ] Implement `pipeline/encryption.py` functions
- [ ] Test encrypt → decrypt round-trip on a sample text file

**Deliverable:** Working encryption module with passing round-trip test.

---

## Phase 4 — Synthetic Data Generator (~3 hours)
- [ ] Implement `data_gen/generate_test_data.py`
- [ ] Use faker for all PII-like fields
- [ ] Match real Bread application feed field layout
- [ ] Add `inject_bad_records` for reject rule testing
- [ ] Write pipe-delimited output
- [ ] Implement `data_gen/upload_to_s3.py` (encrypt + upload)
- [ ] Test: one command produces an encrypted file in inbound bucket

**Deliverable:** Encrypted 50K-record file in S3 inbound bucket.

---

## Phase 5 — Postgres Schema (~2 hours)
- [ ] Run `sql/schema.sql` against Postgres
- [ ] Run `sql/seed_suppression_data.sql` to pre-load suppression tables
- [ ] Connect with DBeaver, verify all tables present
- [ ] Verify indexes created

**Deliverable:** All tables exist and are queryable in DBeaver.

---

## Phase 6 — Reject Rules Engine (~4 hours)
- [ ] Implement `PreProcessRejectEngine.apply_rules()`
- [ ] Implement each `_apply_*` helper
- [ ] Wire up the threshold check
- [ ] Write tests in `tests/test_reject_rules.py`
- [ ] Run tests, fix until passing
- [ ] Manual end-to-end test with 10K-record file

**Deliverable:** Engine splits a file into clean/rejected with passing tests.

---

## Phase 7 — Suppression Engine (~4 hours)
- [ ] Implement `SuppressionEngine.load_suppression_lists()`
- [ ] Implement `apply_suppressions()`
- [ ] Implement `log_excluded_to_db()`
- [ ] Write tests in `tests/test_suppression_engine.py`
- [ ] Run tests, fix until passing
- [ ] Manual test: confirm known suppressed records get excluded

**Deliverable:** Suppression engine works end-to-end with audit logging.

---

## Phase 8 — Identity Resolution (~5 hours)
- [ ] Implement `normalize_field()` and `compute_identity_hash()`
- [ ] Implement `IdentityResolver.resolve_identities()` (v1 hash-based)
- [ ] Verify second run of same file produces match rate >60%
- [ ] (Optional v2) Add recordlinkage probabilistic matching

**Deliverable:** Identity resolution attaches indiv_id to every clean record.

---

## Phase 9 — Warehouse Loader (~3 hours)
- [ ] Implement `load_to_postgres()` with bulk insert
- [ ] Implement `load_to_snowflake()` using write_pandas
- [ ] Implement `load_to_both_warehouses()`
- [ ] Test: load 50K records, verify count matches in both warehouses

**Deliverable:** Same records in both Postgres and Snowflake, counts match.

---

## Phase 10 — SQL Audit Layer (~2 hours)
- [ ] Implement `run_audit_queries()`
- [ ] Implement `write_audit_log()`
- [ ] Implement `check_volume_anomaly()`
- [ ] Test: after a pipeline run, audit log has a populated row

**Deliverable:** Audit log captures full pipeline metrics after each run.

---

## Phase 11 — Airflow DAG Wiring (~6 hours)
- [ ] Configure Airflow to use Postgres backend (not SQLite)
- [ ] Implement each task callable in `dags/application_pipeline.py`
- [ ] Pass context between tasks via XCom
- [ ] Test DAG manually via Airflow UI
- [ ] Configure systemd services for scheduler and webserver
- [ ] Verify DAG persists across reboots

**Deliverable:** Drop a file in S3, watch DAG run green end-to-end.

---

## Phase 12 — Streamlit Dashboard (~3 hours)
- [ ] Implement queries in `dashboard/app.py`
- [ ] Wire up Plotly charts
- [ ] Run as systemd service on port 8501
- [ ] Access from laptop browser, verify metrics populate

**Deliverable:** Live dashboard at http://[pi-ip]:8501.

---

## Phase 13 — Slack Alerting (~1 hour)
- [ ] Create personal Slack workspace
- [ ] Add bot, get token, store in `.env`
- [ ] Implement `send_success_alert` and `send_failure_alert`
- [ ] Wire `airflow_failure_callback` into DAG default_args
- [ ] Test: trigger a failure, verify Slack ping

**Deliverable:** Slack pings on every success and failure with metrics.

---

## Phase 14 — Dockerize + Document (~5 hours)
- [ ] Finalize `docker-compose.yml`
- [ ] Write `dashboard/Dockerfile`
- [ ] Test full stack with `docker compose up`
- [ ] Take screenshots of Airflow DAG, dashboard, Slack alerts
- [ ] Draw architecture diagram (excalidraw or draw.io)
- [ ] Flesh out README with screenshots and diagram
- [ ] Add GitHub Actions workflow

**Deliverable:** Anyone can `git clone && docker compose up` and run it.

---

## Phase 15 — Polish + Post (~3 hours)
- [ ] Final code review and cleanup
- [ ] Push to public GitHub repo
- [ ] Wait 24 hours, re-read everything fresh
- [ ] Draft LinkedIn post (no preamble, attach diagram screenshot)
- [ ] Post

**Deliverable:** Public GitHub repo, LinkedIn post live.

---

## Total Estimate
**50-60 hours** over 2-3 weeks of evenings and weekends.
