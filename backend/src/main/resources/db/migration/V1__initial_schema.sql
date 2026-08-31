BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE account_status AS ENUM ('ACTIVE', 'SUSPENDED', 'CLOSED');
CREATE TYPE transaction_status AS ENUM ('PENDING', 'ALLOW', 'REVIEW', 'HOLD', 'DECLINED', 'RISK_UNAVAILABLE');
CREATE TYPE risk_case_status AS ENUM ('OPEN', 'IN_REVIEW', 'RESOLVED');
CREATE TYPE risk_severity AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE analyst_decision_type AS ENUM ('ALLOW', 'VERIFY', 'HOLD', 'CONFIRMED_ABUSE', 'FALSE_POSITIVE');

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(64) NOT NULL UNIQUE,
    account_type VARCHAR(32) NOT NULL DEFAULT 'USER',
    status account_status NOT NULL DEFAULT 'ACTIVE',
    country_code CHAR(2) NOT NULL DEFAULT 'IN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    category_code VARCHAR(32),
    country_code CHAR(2) NOT NULL DEFAULT 'IN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id VARCHAR(128) NOT NULL UNIQUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(64) NOT NULL UNIQUE,
    sender_account_id VARCHAR(64) NOT NULL,
    receiver_id VARCHAR(64) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    device_id VARCHAR(128),
    ip_address INET,
    payment_method VARCHAR(32) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status transaction_status NOT NULL DEFAULT 'PENDING',
    risk_score NUMERIC(5, 4) CHECK (risk_score BETWEEN 0 AND 1),
    raw_payload JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE TABLE risk_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(64) NOT NULL UNIQUE,
    transaction_id VARCHAR(64) NOT NULL REFERENCES transactions(transaction_id),
    account_id VARCHAR(64) NOT NULL,
    status risk_case_status NOT NULL DEFAULT 'OPEN',
    severity risk_severity NOT NULL,
    transaction_risk NUMERIC(5, 4) CHECK (transaction_risk BETWEEN 0 AND 1),
    account_risk NUMERIC(5, 4) CHECK (account_risk BETWEEN 0 AND 1),
    behavior_risk NUMERIC(5, 4) CHECK (behavior_risk BETWEEN 0 AND 1),
    temporal_risk NUMERIC(5, 4) CHECK (temporal_risk BETWEEN 0 AND 1),
    structural_risk NUMERIC(5, 4) CHECK (structural_risk BETWEEN 0 AND 1),
    similarity_risk NUMERIC(5, 4) CHECK (similarity_risk BETWEEN 0 AND 1),
    ring_risk NUMERIC(5, 4) CHECK (ring_risk BETWEEN 0 AND 1),
    confidence NUMERIC(5, 4) CHECK (confidence BETWEEN 0 AND 1),
    recommendation VARCHAR(64),
    ai_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE risk_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_case_id UUID NOT NULL REFERENCES risk_cases(id) ON DELETE CASCADE,
    signal_type VARCHAR(64) NOT NULL,
    source_engine VARCHAR(32) NOT NULL,
    score NUMERIC(5, 4) CHECK (score BETWEEN 0 AND 1),
    description TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE analyst_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_case_id UUID NOT NULL REFERENCES risk_cases(id) ON DELETE CASCADE,
    decision analyst_decision_type NOT NULL,
    analyst_id VARCHAR(128) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE fraud_case_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    risk_case_id UUID NOT NULL UNIQUE REFERENCES risk_cases(id) ON DELETE CASCADE,
    final_label analyst_decision_type NOT NULL,
    case_summary TEXT NOT NULL,
    feature_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB,
    evidence_snapshot JSONB NOT NULL DEFAULT '[]'::JSONB,
    qdrant_point_id UUID UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_sender_time ON transactions (sender_account_id, occurred_at DESC);
CREATE INDEX idx_transactions_receiver_time ON transactions (receiver_id, occurred_at DESC);
CREATE INDEX idx_transactions_device_time ON transactions (device_id, occurred_at DESC);
CREATE INDEX idx_transactions_status_time ON transactions (status, occurred_at DESC);
CREATE INDEX idx_risk_cases_status_created ON risk_cases (status, created_at DESC);
CREATE INDEX idx_risk_cases_account_created ON risk_cases (account_id, created_at DESC);
CREATE INDEX idx_risk_signals_case ON risk_signals (risk_case_id);
CREATE INDEX idx_analyst_decisions_case ON analyst_decisions (risk_case_id, created_at DESC);
CREATE INDEX idx_transactions_raw_payload_gin ON transactions USING GIN (raw_payload);

COMMIT;
