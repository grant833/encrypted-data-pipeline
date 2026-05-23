-- Seed privacy suppression and fraud watchlist tables with synthetic data.

INSERT INTO privacy_opt_outs (case_number, email_address, first_name, last_name) VALUES
    ('PRIV-OO-0001', 'john.doe@example.com',     'John',    'Doe'),
    ('PRIV-OO-0002', 'jane.smith@example.com',   'Jane',    'Smith'),
    ('PRIV-OO-0003', 'bob.jones@example.com',    'Bob',     'Jones'),
    ('PRIV-OO-0004', 'alice.brown@example.com',  'Alice',   'Brown'),
    ('PRIV-OO-0005', 'charlie.davis@example.com','Charlie', 'Davis');

INSERT INTO privacy_deletes (case_number, email_address) VALUES
    ('PRIV-DEL-0001', 'delete.me@example.com'),
    ('PRIV-DEL-0002', 'remove.account@example.com'),
    ('PRIV-DEL-0003', 'gdpr.request@example.com');

INSERT INTO fraud_watchlist (application_id, flag_reason) VALUES
    ('APP-FRAUD0000001', 'fraudulent_application'),
    ('APP-FRAUD0000002', 'repeated_declines'),
    ('APP-FRAUD0000003', 'identity_theft_flag');
