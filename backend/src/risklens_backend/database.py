import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .models import (
    AnalystAction,
    AnalystDecision,
    AnalystDecisionRequest,
    CaseMemoryRequest,
    RiskCaseDetail,
    RiskCaseSummary,
    RiskEvaluation,
    RiskSeverity,
    StoredRiskSignal,
    TransactionDetail,
    TransactionRequest,
)


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class Repository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def health(self) -> bool:
        try:
            with self.connect() as connection:
                connection.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    def insert_transaction(self, payload: TransactionRequest) -> None:
        values = payload.model_dump(mode="json")
        try:
            with self.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO transactions (
                        transaction_id, sender_account_id, receiver_id, amount, currency,
                        device_id, ip_address, payment_method, occurred_at, ip_id,
                        payment_instrument_id, location_city, location_state, location_country,
                        authorization_status, authentication_status, processing_status,
                        failure_reason, merchant_category, context, raw_payload
                    ) VALUES (
                        %(transaction_id)s, %(sender_id)s, %(receiver_id)s, %(amount)s,
                        %(currency)s, %(device_id)s, %(ip_address)s, %(payment_method)s,
                        %(timestamp)s, %(ip_id)s, %(payment_instrument_id)s, %(location_city)s,
                        %(location_state)s, %(location_country)s, %(authorization_status)s,
                        %(authentication_status)s, %(transaction_status)s, %(failure_reason)s,
                        %(merchant_category)s, %(context)s, %(raw_payload)s
                    )
                    """,
                    {**values, "context": Jsonb(values["context"]), "raw_payload": Jsonb(values)},
                )
        except UniqueViolation as error:
            raise ConflictError(f"Transaction already exists: {payload.transaction_id}") from error

    def mark_risk_unavailable(self, transaction_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE transactions SET status = 'RISK_UNAVAILABLE' WHERE transaction_id = %s",
                (transaction_id,),
            )

    def store_evaluation(
        self,
        payload: TransactionRequest,
        evaluation: RiskEvaluation,
        review_threshold: float,
    ) -> str | None:
        status = evaluation.decision
        risk_score = round(evaluation.overall_risk, 4)
        create_case = status in {"REVIEW", "HOLD", "DECLINED"} or risk_score >= review_threshold
        case_id = f"CASE-{uuid4().hex[:12].upper()}" if create_case else None

        with self.connect() as connection:
            connection.execute(
                """
                UPDATE transactions SET status = %s, risk_score = %s
                WHERE transaction_id = %s
                """,
                (status, risk_score, payload.transaction_id),
            )
            if not case_id:
                return None

            case_row = connection.execute(
                """
                INSERT INTO risk_cases (
                    case_id, transaction_id, account_id, severity, transaction_risk,
                    account_risk, behavior_risk, temporal_risk, structural_risk,
                    similarity_risk, ring_risk, confidence, recommendation, ai_summary
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
                """,
                (
                    case_id,
                    payload.transaction_id,
                    payload.sender_id,
                    _severity(evaluation.overall_risk),
                    evaluation.transaction_risk,
                    evaluation.account_risk,
                    evaluation.behavior_risk,
                    evaluation.temporal_risk,
                    evaluation.structural_risk,
                    evaluation.similarity_risk,
                    evaluation.ring_risk,
                    evaluation.confidence,
                    evaluation.recommendation,
                    evaluation.summary,
                ),
            ).fetchone()
            risk_case_id = case_row["id"]
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO risk_signals (
                        risk_case_id, signal_type, source_engine, score, description, evidence
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            risk_case_id,
                            signal.type or "UNKNOWN",
                            signal.source or "RISK_SERVICE",
                            signal.score,
                            signal.description or "Risk signal detected",
                            Jsonb(signal.evidence),
                        )
                        for signal in evaluation.signals
                    ],
                )
        return case_id

    def get_transaction(self, transaction_id: str) -> TransactionDetail:
        with self.connect() as connection:
            row = connection.execute(
                _TRANSACTION_SELECT + " WHERE t.transaction_id = %s", (transaction_id,)
            ).fetchone()
        if not row:
            raise NotFoundError(f"Transaction not found: {transaction_id}")
        return TransactionDetail.model_validate(row)

    def list_transactions(
        self, limit: int, account_id: str | None = None
    ) -> list[TransactionDetail]:
        where = " WHERE t.sender_account_id = %s" if account_id else ""
        params: tuple[Any, ...] = (account_id, limit) if account_id else (limit,)
        with self.connect() as connection:
            rows = connection.execute(
                _TRANSACTION_SELECT + where + " ORDER BY t.occurred_at DESC LIMIT %s", params
            ).fetchall()
        return [TransactionDetail.model_validate(row) for row in rows]

    def list_cases(
        self,
        limit: int,
        status: str | None = None,
        severity: str | None = None,
        linked_only: bool = False,
        review_threshold: float = 0.75,
    ) -> list[RiskCaseSummary]:
        conditions: list[str] = []
        params: list[Any] = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if severity:
            conditions.append("severity = %s")
            params.append(severity)
        if linked_only:
            conditions.extend(["status IN ('OPEN', 'IN_REVIEW')", "ring_risk >= %s"])
            params.append(review_threshold)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order = "ring_risk DESC, created_at DESC" if linked_only else "created_at DESC"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                _CASE_SUMMARY_SELECT + where + f" ORDER BY {order} LIMIT %s", params
            ).fetchall()
        return [RiskCaseSummary.model_validate(row) for row in rows]

    def get_case(self, case_id: str) -> RiskCaseDetail:
        with self.connect() as connection:
            case = connection.execute(
                """
                SELECT case_id, transaction_id, account_id, status, severity,
                       transaction_risk, account_risk, behavior_risk, temporal_risk,
                       structural_risk, similarity_risk, ring_risk, confidence,
                       recommendation, ai_summary, created_at, updated_at, resolved_at
                FROM risk_cases WHERE case_id = %s
                """,
                (case_id,),
            ).fetchone()
            if not case:
                raise NotFoundError(f"Risk case not found: {case_id}")
            signals = connection.execute(
                """
                SELECT signal_type AS type, source_engine AS source, score, description,
                       evidence::text AS evidence, created_at
                FROM risk_signals WHERE risk_case_id = (
                    SELECT id FROM risk_cases WHERE case_id = %s
                ) ORDER BY created_at
                """,
                (case_id,),
            ).fetchall()
            decisions = connection.execute(
                """
                SELECT id, decision, analyst_id AS analyst, comment, created_at
                FROM analyst_decisions WHERE risk_case_id = (
                    SELECT id FROM risk_cases WHERE case_id = %s
                ) ORDER BY created_at DESC
                """,
                (case_id,),
            ).fetchall()
        return RiskCaseDetail.model_validate(
            {
                **case,
                "signals": [StoredRiskSignal.model_validate(row) for row in signals],
                "decisions": [AnalystDecision.model_validate(row) for row in decisions],
            }
        )

    def list_actions(self, limit: int) -> list[AnalystAction]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, c.case_id, c.transaction_id, c.account_id, d.decision,
                       d.analyst_id AS analyst, d.comment, d.created_at
                FROM analyst_decisions d
                JOIN risk_cases c ON c.id = d.risk_case_id
                ORDER BY d.created_at DESC LIMIT %s
                """,
                (limit,),
            ).fetchall()
        return [AnalystAction.model_validate(row) for row in rows]

    def decide(
        self, case_id: str, request: AnalystDecisionRequest
    ) -> tuple[AnalystDecision, CaseMemoryRequest]:
        try:
            with self.connect() as connection:
                risk_case = connection.execute(
                    "SELECT * FROM risk_cases WHERE case_id = %s FOR UPDATE", (case_id,)
                ).fetchone()
                if not risk_case:
                    raise NotFoundError(f"Risk case not found: {case_id}")
                if risk_case["status"] == "RESOLVED":
                    raise ConflictError(f"Risk case is already resolved: {case_id}")

                decision = connection.execute(
                    """
                    INSERT INTO analyst_decisions (risk_case_id, decision, analyst_id, comment)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, decision, analyst_id AS analyst, comment, created_at
                    """,
                    (risk_case["id"], request.decision, request.analyst, request.comment),
                ).fetchone()
                connection.execute(
                    """
                    UPDATE risk_cases
                    SET status = 'RESOLVED', resolved_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (risk_case["id"],),
                )
                signals = connection.execute(
                    """
                    SELECT signal_type AS type, source_engine AS source, score,
                           description, evidence
                    FROM risk_signals WHERE risk_case_id = %s ORDER BY created_at
                    """,
                    (risk_case["id"],),
                ).fetchall()
        except UniqueViolation as error:
            raise ConflictError(f"Risk case is already resolved: {case_id}") from error

        memory = _memory_request(risk_case, request, signals)
        return AnalystDecision.model_validate(decision), memory


_TRANSACTION_SELECT = """
SELECT t.transaction_id, t.sender_account_id AS sender_id, t.receiver_id,
       t.amount, t.currency, t.device_id, host(t.ip_address) AS ip_address,
       t.payment_method, t.ip_id, t.payment_instrument_id, t.location_city,
       t.location_state, t.location_country, t.authorization_status,
       t.authentication_status, t.processing_status AS transaction_status,
       t.failure_reason, t.merchant_category, t.context, t.occurred_at AS timestamp,
       t.received_at, t.status, t.risk_score, c.case_id
FROM transactions t LEFT JOIN risk_cases c ON c.transaction_id = t.transaction_id
"""

_CASE_SUMMARY_SELECT = """
SELECT case_id, transaction_id, account_id, status, severity,
       ring_risk, confidence, recommendation, created_at
FROM risk_cases
"""


def _severity(score: float) -> RiskSeverity:
    if score >= 0.90:
        return RiskSeverity.CRITICAL
    if score >= 0.75:
        return RiskSeverity.HIGH
    if score >= 0.50:
        return RiskSeverity.MEDIUM
    return RiskSeverity.LOW


def _memory_request(
    risk_case: dict[str, Any],
    request: AnalystDecisionRequest,
    signals: list[dict[str, Any]],
) -> CaseMemoryRequest:
    dimensions = (
        "transaction_risk",
        "account_risk",
        "behavior_risk",
        "temporal_risk",
        "structural_risk",
        "similarity_risk",
        "ring_risk",
        "confidence",
    )
    note = f" Analyst note: {request.comment}" if request.comment else ""
    summary = (
        f"Analyst resolved {risk_case['case_id']} as {request.decision}. "
        f"{risk_case.get('ai_summary') or ''}{note}"
    ).strip()
    evidence = []
    for signal in signals:
        item = dict(signal)
        if isinstance(item.get("evidence"), str):
            try:
                item["evidence"] = json.loads(item["evidence"])
            except json.JSONDecodeError:
                item["evidence"] = {"raw": item["evidence"]}
        evidence.append(item)
    return CaseMemoryRequest(
        risk_case_id=risk_case["case_id"],
        final_label=request.decision,
        case_summary=summary,
        feature_snapshot={
            "severity": risk_case["severity"],
            **{name.removesuffix("_risk"): risk_case.get(name) for name in dimensions},
        },
        evidence_snapshot=evidence,
    )
