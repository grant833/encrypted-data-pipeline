-- ============================================================================
-- Pipeline Project — Warehouse Schema
-- ============================================================================
-- Mirrors the table layouts used in production at Acxiom for the application
-- feed processing chain. All data is synthetic.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Warehouse: Application table (mirrors WH_CL_APPLICATION)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS wh_cl_application CASCADE;
CREATE TABLE wh_cl_application (
    record_id          SERIAL PRIMARY KEY,
    data_collection_id VARCHAR(50)  NOT NULL,
    data_src_cd        VARCHAR(20)  DEFAULT 'APPLICATIONS',
    ek_data_src_cd     VARCHAR(20)  DEFAULT 'BREAD',
    application_id     VARCHAR(20)  UNIQUE NOT NULL,
    acct_id            VARCHAR(25),
    indiv_id           BIGINT,
    first_name         VARCHAR(50),
    middle_init        VARCHAR(1),
    last_name          VARCHAR(50),
    str_addr           VARCHAR(100),
    city               VARCHAR(20),
    state              VARCHAR(2),
    zip_cd             VARCHAR(5),
    div_no             INTEGER,
    entry_date         DATE,
    app_status_flag    VARCHAR(1),
    email_addr         VARCHAR(80),
    birth_date         DATE,
    load_timestamp     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wh_cl_app_run        ON wh_cl_application (data_collection_id);
CREATE INDEX idx_wh_cl_app_indiv      ON wh_cl_application (indiv_id);
CREATE INDEX idx_wh_cl_app_email      ON wh_cl_application (email_addr);


-- ----------------------------------------------------------------------------
-- Warehouse: Identity table (mirrors WH_IDENTITY)
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS wh_identity CASCADE;
CREATE TABLE wh_identity (
    indiv_id              BIGSERIAL PRIMARY KEY,
    source_hash           VARCHAR(64) UNIQUE NOT NULL,
    data_src_cd           VARCHAR(20),
    abilitec_consumerlink VARCHAR(50),
    first_name            VARCHAR(50),
    last_name             VARCHAR(50),
    str_addr              VARCHAR(100),
    city                  VARCHAR(20),
    state                 VARCHAR(2),
    zip_cd                VARCHAR(5),
    email                 VARCHAR(80),
    year_of_birth         VARCHAR(4),
    first_seen_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_wh_identity_hash ON wh_identity (source_hash);


-- ----------------------------------------------------------------------------
-- Suppression tables
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS ccpa_donotsell CASCADE;
CREATE TABLE ccpa_donotsell (
    casenumber    VARCHAR(20) PRIMARY KEY,
    email_addr    VARCHAR(80) NOT NULL,
    first_name    VARCHAR(50),
    last_name     VARCHAR(50),
    request_date  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ccpa_donotsell_email ON ccpa_donotsell (email_addr);


DROP TABLE IF EXISTS ccpa_delete CASCADE;
CREATE TABLE ccpa_delete (
    casenumber    VARCHAR(20) PRIMARY KEY,
    email_addr    VARCHAR(80) NOT NULL,
    request_date  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ccpa_delete_email ON ccpa_delete (email_addr);


DROP TABLE IF EXISTS credit_abusers CASCADE;
CREATE TABLE credit_abusers (
    application_id  VARCHAR(20) PRIMARY KEY,
    flagged_reason  VARCHAR(100),
    load_date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ----------------------------------------------------------------------------
-- Suppression exclusions log — every record excluded by the engine
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS suppression_exclusions CASCADE;
CREATE TABLE suppression_exclusions (
    exclusion_id        BIGSERIAL PRIMARY KEY,
    pipeline_run_id     VARCHAR(50) NOT NULL,
    application_id      VARCHAR(20),
    email_addr          VARCHAR(80),
    suppression_source  VARCHAR(50),
    excluded_timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_supp_exc_run ON suppression_exclusions (pipeline_run_id);


-- ----------------------------------------------------------------------------
-- Rejected records — every record that failed reject rules
-- ----------------------------------------------------------------------------
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


-- ----------------------------------------------------------------------------
-- Pipeline audit log — one row per stage per run
-- ----------------------------------------------------------------------------
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
