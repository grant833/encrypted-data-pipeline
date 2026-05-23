-- ============================================================================
-- Seed suppression tables with synthetic data
-- ============================================================================
-- Run this after schema.sql to pre-populate suppression tables. This gives
-- the suppression engine something to match against during testing.
--
-- For larger volumes (10K+ records), use data_gen/generate_test_data.py
-- to generate suppression files and load via the loader instead.
-- ============================================================================


-- A few sample CCPA opt-outs
INSERT INTO ccpa_donotsell (casenumber, email_addr, first_name, last_name) VALUES
    ('CCPA-DNS-0001', 'john.doe@example.com',     'John',    'Doe'),
    ('CCPA-DNS-0002', 'jane.smith@example.com',   'Jane',    'Smith'),
    ('CCPA-DNS-0003', 'bob.jones@example.com',    'Bob',     'Jones'),
    ('CCPA-DNS-0004', 'alice.brown@example.com',  'Alice',   'Brown'),
    ('CCPA-DNS-0005', 'charlie.davis@example.com','Charlie', 'Davis');


-- A few sample CCPA delete requests
INSERT INTO ccpa_delete (casenumber, email_addr) VALUES
    ('CCPA-DEL-0001', 'delete.me@example.com'),
    ('CCPA-DEL-0002', 'remove.account@example.com'),
    ('CCPA-DEL-0003', 'gdpr.request@example.com');


-- A few sample credit abusers
INSERT INTO credit_abusers (application_id, flagged_reason) VALUES
    ('APP-FRAUD-0001', 'Fraudulent application'),
    ('APP-FRAUD-0002', 'Repeated declined applications'),
    ('APP-FRAUD-0003', 'Identity theft flag');
