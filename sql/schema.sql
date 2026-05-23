-- ============================================================================
-- Encrypted Data Pipeline — Warehouse Schema
-- ============================================================================
-- Generic consumer finance data pipeline. All data is synthetic.
-- ============================================================================


-- Customer applications table (main warehouse target)
DROP TABLE IF EXISTS customer_applications CASCADE;
CREATE TABLE customer_applications (
    record_id            SERIAL PRIMARY KEY,
    pipeline_run_id      VARCHAR(50)  NOT NULL,
    source_system        VARCHAR(20)  DEFAULT 'NORTHSTAR_FINANCIAL',
    application_id       VARCHAR(20)  UNIQUE NOT NULL,
    customer_id          VARCHAR(25),
    identity_id          BIGINT,
    first_name           VARCHAR(50),
    middle_initial       VARCHAR(1),
    last_name            VARCHAR(50),
    street_address       VARCHAR(100),
    city                 VARCHAR(20),
    state                VARCHAR(2),
    zip_code             VARCHAR(5),
    division_id          INTEGER,
    submitted_date       DATE,
    application_status   VARCHAR(20),
    email_address        VARCHAR(80),
    date_of_birth        DATE,
    load_timestamp       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cust_app_run    ON customer_applications (pipeline_run_id);
CREATE INDEX idx_cust_app_ident  ON customer_applications (identity_id);
CREATE INDEX idx_cust_app_email  ON customer_applications (email_address);


-- Identity resolution table
DROP TABLE IF EXISTS identities CASCADE;
CREATE TABLE identities (
    identity_id           BIGSERIAL PRIMARY KEY,
    identity_hash         VARCHAR(64) UNIQUE NOT NULL,
    source_system         VARCHAR(20),
    external_match_id     VARCHAR(50),
    first_name            VARCHAR(50),
    last_name             VARCHAR(50),
    street_address        VARCHAR(100),
    city                  VARCHAR(20),
    state                 VARCHAR(2),
    zip_code              VARCHAR(5),
    email_address         VARCHAR(80),
    year_of_birth         VARCHAR(4),
    first_seen_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_identity_hash ON identities (identity_hash);


-- Privacy suppression — opt-outs
DROP TABLE IF EXISTS privacy_opt_outs CASCADE;
CREATE TABLE privacy_opt_outs (
    case_number    VARCHAR(20) PRIMARY KEY,
    email_address  VARCHAR(80) NOT NULL,
    first_name     VARCHAR(50),
    last_name      VARCHAR(50),
    request_date   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_opt_outs_email ON privacy_opt_outs (email_address);


-- Privacy suppression — delete requests
DROP TABLE IF EXISTS privacy_deletes CASCADE;
CREATE TABLE privacy_deletes (
    case_number    VARCHAR(20) PRIMARY KEY,
    email_address  VARCHAR(80) NOT NULL,
    request_date   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_deletes_email ON privacy_deletes (email_address);


-- Fraud watchlist
DROP TABLE IF EXISTS fraud_watchlist CASCADE;
CREATE TABLE fraud_watchlist (
    application_id  VARCHAR(20) PRIMARY KEY,
    flag_reason     VARCHAR(100),
    load_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Suppression exclusions log
DROP TABLE IF EXISTS suppression_exclusions CASCADE;
CREATE TABLE suppression_exclusions (
    exclusion_id        BIGSERIAL PRIMARY KEY,
    pipeline_run_id     VARCHAR(50) NOT NULL,
    application_id      VARCHAR(20),
    email_address       VARCHAR(80),
    suppression_source  VARCHAR(50),
    excluded_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_supp_exc_run ON suppression_exclusions (pipeline_run_id);


-- Rejected records log
DROP TABLE IF EXISTS rejected_records CASCADE;
CREATE TABLE rejected_records (
    reject_id           BIGSERIAL PRIMARY KEY,
    pipeline_run_id     VARCHAR(50) NOT NULL,
    application_id      VARCHAR(20),
    reject_reason       VARCHAR(200),
    raw_record          JSONB,
    rejected_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_rejected_run ON rejected_records (pipeline_run_id);


-- Pipeline audit log
DROP TABLE IF EXISTS pipeline_audit_log CASCADE;
CREATE TABLE pipeline_audit_log (
    audit_id           BIGSERIAL PRIMARY KEY,
    pipeline_run_id    VARCHAR(50) NOT NULL,
    feed_name          VARCHAR(50),
    stage              VARCHAR(50),
    record_count       INTEGER,
    rejected_count     INTEGER,
    suppressed_count   INTEGER,
    runtime_seconds    NUMERIC(10, 2),
    status             VARCHAR(20),
    error_message      TEXT,
    run_timestamp      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_run  ON pipeline_audit_log (pipeline_run_id);
CREATE INDEX idx_audit_feed ON pipeline_audit_log (feed_name, run_timestamp);
