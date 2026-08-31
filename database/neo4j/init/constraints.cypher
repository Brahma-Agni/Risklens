CREATE CONSTRAINT account_id_unique IF NOT EXISTS
FOR (n:Account) REQUIRE n.accountId IS UNIQUE;

CREATE CONSTRAINT merchant_id_unique IF NOT EXISTS
FOR (n:Merchant) REQUIRE n.merchantId IS UNIQUE;

CREATE CONSTRAINT beneficiary_id_unique IF NOT EXISTS
FOR (n:Beneficiary) REQUIRE n.beneficiaryId IS UNIQUE;

CREATE CONSTRAINT device_id_unique IF NOT EXISTS
FOR (n:Device) REQUIRE n.deviceId IS UNIQUE;

CREATE CONSTRAINT ip_address_unique IF NOT EXISTS
FOR (n:IPAddress) REQUIRE n.address IS UNIQUE;

CREATE CONSTRAINT transaction_id_unique IF NOT EXISTS
FOR (n:Transaction) REQUIRE n.transactionId IS UNIQUE;

CREATE CONSTRAINT risk_case_id_unique IF NOT EXISTS
FOR (n:RiskCase) REQUIRE n.caseId IS UNIQUE;

CREATE INDEX account_risk_score IF NOT EXISTS
FOR (n:Account) ON (n.riskScore);

CREATE INDEX transaction_occurred_at IF NOT EXISTS
FOR (n:Transaction) ON (n.occurredAt);

CREATE INDEX risk_case_status IF NOT EXISTS
FOR (n:RiskCase) ON (n.status);

