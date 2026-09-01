ALTER TABLE transactions
    ADD COLUMN ip_id VARCHAR(128),
    ADD COLUMN payment_instrument_id VARCHAR(128),
    ADD COLUMN location_city VARCHAR(128),
    ADD COLUMN location_state VARCHAR(128),
    ADD COLUMN location_country CHAR(2),
    ADD COLUMN authorization_status VARCHAR(32),
    ADD COLUMN authentication_status VARCHAR(32),
    ADD COLUMN processing_status VARCHAR(32),
    ADD COLUMN failure_reason VARCHAR(64),
    ADD COLUMN merchant_category VARCHAR(64),
    ADD COLUMN context JSONB NOT NULL DEFAULT '{}'::JSONB;

CREATE INDEX idx_transactions_ip_id_time
    ON transactions (ip_id, occurred_at DESC)
    WHERE ip_id IS NOT NULL;

CREATE INDEX idx_transactions_instrument_time
    ON transactions (payment_instrument_id, occurred_at DESC)
    WHERE payment_instrument_id IS NOT NULL;

CREATE INDEX idx_transactions_merchant_category_time
    ON transactions (merchant_category, occurred_at DESC)
    WHERE merchant_category IS NOT NULL;

CREATE INDEX idx_transactions_context_gin ON transactions USING GIN (context);
