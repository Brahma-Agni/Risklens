-- Minimal local-development reference data. Synthetic transaction ground truth
-- intentionally belongs in the evaluation dataset, never in runtime tables.

INSERT INTO accounts (account_id, account_type)
VALUES
    ('USER-DEMO-001', 'USER'),
    ('USER-DEMO-002', 'USER')
ON CONFLICT (account_id) DO NOTHING;

INSERT INTO merchants (merchant_id, display_name, category_code)
VALUES
    ('MERCHANT-DEMO-001', 'RiskLens Demo Merchant', '7399')
ON CONFLICT (merchant_id) DO NOTHING;

