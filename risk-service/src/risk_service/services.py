import asyncio
import logging
from typing import Protocol

import httpx
import psycopg
from neo4j import AsyncDriver, AsyncGraphDatabase

from risk_service.embedding import HashingEmbedder
from risk_service.engines import clamp
from risk_service.models import (
    Decision,
    EngineResult,
    HistoricalTransaction,
    RiskRequest,
    RiskSignal,
)

logger = logging.getLogger(__name__)


class RequiredDependencyError(RuntimeError):
    pass


class HistoryStore(Protocol):
    async def history(self, request: RiskRequest, limit: int) -> list[HistoricalTransaction]: ...

    async def health(self) -> bool: ...


class GraphStore(Protocol):
    async def analyze(self, request: RiskRequest) -> EngineResult: ...

    async def health(self) -> bool: ...


class SimilarityStore(Protocol):
    async def analyze(self, request: RiskRequest, context: str) -> EngineResult: ...

    async def health(self) -> bool: ...


class VerificationClient(Protocol):
    async def verify(
        self,
        request: RiskRequest,
        *,
        decision: Decision,
        recommendation: str,
        confidence: float,
        dimensions: dict[str, float],
        signals: list[RiskSignal],
        summary: str,
    ) -> tuple[Decision, str, float, list[RiskSignal]]: ...

    async def health(self) -> bool: ...


class PostgresHistoryStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    async def history(self, request: RiskRequest, limit: int) -> list[HistoricalTransaction]:
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                cursor = await connection.execute(
                    """
                    SELECT transaction_id, amount::float8, receiver_id, device_id,
                           host(ip_address), payment_method, occurred_at, status::text,
                           ip_id, payment_instrument_id, authorization_status,
                           authentication_status, processing_status, failure_reason,
                           merchant_category
                    FROM transactions
                    WHERE sender_account_id = %s
                      AND transaction_id <> %s
                      AND occurred_at <= %s
                    ORDER BY occurred_at DESC
                    LIMIT %s
                    """,
                    (request.sender_id, request.transaction_id, request.timestamp, limit),
                )
                rows = await cursor.fetchall()
        except psycopg.Error as error:
            raise RequiredDependencyError(
                "PostgreSQL transaction history is unavailable"
            ) from error
        return [
            HistoricalTransaction(
                transaction_id=row[0],
                amount=float(row[1]),
                receiver_id=row[2],
                device_id=row[3],
                ip_address=row[4],
                payment_method=row[5],
                timestamp=row[6],
                status=row[7],
                ip_id=row[8],
                payment_instrument_id=row[9],
                authorization_status=row[10],
                authentication_status=row[11],
                transaction_status=row[12],
                failure_reason=row[13],
                merchant_category=row[14],
            )
            for row in rows
        ]

    async def health(self) -> bool:
        try:
            async with await psycopg.AsyncConnection.connect(self.database_url) as connection:
                cursor = await connection.execute("SELECT 1")
                return (await cursor.fetchone()) == (1,)
        except psycopg.Error:
            return False


class Neo4jGraphStore:
    QUERY = """
    MERGE (a:Account {accountId: $sender})
    MERGE (b:Beneficiary {beneficiaryId: $receiver})
    MERGE (t:Transaction {transactionId: $transaction})
      ON CREATE SET t.occurredAt = datetime($timestamp), t.amount = $amount
    MERGE (t)-[:INITIATED_BY]->(a)
    MERGE (t)-[:SENT_TO]->(b)
    MERGE (a)-[ab:SENT_TO]->(b)
      ON CREATE SET ab.firstSeenAt = datetime($timestamp), ab.transactionCount = 0
      SET ab.lastSeenAt = datetime($timestamp), ab.transactionCount = ab.transactionCount + 1
    FOREACH (_ IN CASE WHEN $device IS NULL THEN [] ELSE [1] END |
      MERGE (d:Device {deviceId: $device})
      MERGE (a)-[ad:USED_DEVICE]->(d)
        ON CREATE SET ad.firstSeenAt = datetime($timestamp)
        SET ad.lastSeenAt = datetime($timestamp)
      MERGE (t)-[:USED_DEVICE]->(d)
    )
    FOREACH (_ IN CASE WHEN $ip IS NULL THEN [] ELSE [1] END |
      MERGE (i:IPAddress {address: $ip})
      MERGE (a)-[ai:USED_IP]->(i)
        ON CREATE SET ai.firstSeenAt = datetime($timestamp)
        SET ai.lastSeenAt = datetime($timestamp)
      MERGE (t)-[:ORIGINATED_FROM]->(i)
    )
    FOREACH (_ IN CASE WHEN $instrument IS NULL THEN [] ELSE [1] END |
      MERGE (p:PaymentInstrument {instrumentId: $instrument})
      MERGE (a)-[ap:USED_INSTRUMENT]->(p)
        ON CREATE SET ap.firstSeenAt = datetime($timestamp)
        SET ap.lastSeenAt = datetime($timestamp)
      MERGE (t)-[:USED_INSTRUMENT]->(p)
    )
    WITH a, b
    CALL {
      WITH a
      OPTIONAL MATCH (deviceAccount:Account)-[r:USED_DEVICE]->(:Device {deviceId: $device})
      WHERE $device IS NOT NULL
        AND r.lastSeenAt >= datetime($timestamp) - duration('P7D')
      RETURN count(DISTINCT deviceAccount) AS deviceAccounts
    }
    CALL {
      WITH a
      OPTIONAL MATCH (ipAccount:Account)-[r:USED_IP]->(:IPAddress {address: $ip})
      WHERE $ip IS NOT NULL
        AND r.lastSeenAt >= datetime($timestamp) - duration('PT24H')
      RETURN count(DISTINCT ipAccount) AS ipAccounts
    }
    CALL {
      WITH a
      OPTIONAL MATCH (instrumentAccount:Account)-[r:USED_INSTRUMENT]->
        (:PaymentInstrument {instrumentId: $instrument})
      WHERE $instrument IS NOT NULL
        AND r.lastSeenAt >= datetime($timestamp) - duration('P7D')
      RETURN count(DISTINCT instrumentAccount) AS instrumentAccounts
    }
    CALL {
      WITH b
      OPTIONAL MATCH (beneficiarySender:Account)-[r:SENT_TO]->(b)
      WHERE r.lastSeenAt >= datetime($timestamp) - duration('PT1H')
      RETURN count(DISTINCT beneficiarySender) AS beneficiarySenders
    }
    CALL {
      WITH b
      OPTIONAL MATCH (recentTransaction:Transaction)-[:SENT_TO]->(b)
      WHERE recentTransaction.occurredAt >= datetime($timestamp) - duration('PT1H')
        AND recentTransaction.occurredAt <= datetime($timestamp)
      RETURN count(DISTINCT recentTransaction) AS beneficiaryPayments,
             coalesce(sum(recentTransaction.amount), 0) AS beneficiaryAmount
    }
    RETURN deviceAccounts, ipAccounts, instrumentAccounts, beneficiarySenders,
           beneficiaryPayments, beneficiaryAmount
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self) -> None:
        await self.driver.close()

    async def analyze(self, request: RiskRequest) -> EngineResult:
        try:
            async with self.driver.session(database="neo4j") as session:
                result = await session.run(
                    self.QUERY,
                    sender=request.sender_id,
                    receiver=request.receiver_id,
                    transaction=request.transaction_id,
                    timestamp=request.timestamp.isoformat(),
                    amount=request.amount,
                    device=request.device_id,
                    ip=request.ip_address,
                    instrument=request.payment_instrument_id,
                )
                record = await result.single()
                if record is None:
                    raise RuntimeError("Neo4j graph query returned no record")
        except Exception as error:
            logger.warning("Graph analysis unavailable: %s", error)
            return EngineResult(score=0, available=False)

        device_accounts = int(record["deviceAccounts"] or 0)
        ip_accounts = int(record["ipAccounts"] or 0)
        instrument_accounts = int(record["instrumentAccounts"] or 0)
        beneficiary_senders = int(record["beneficiarySenders"] or 0)
        beneficiary_payments = int(record["beneficiaryPayments"] or 0)
        beneficiary_amount = float(record["beneficiaryAmount"] or 0)
        result = relationship_engine(
            request,
            device_accounts=device_accounts,
            ip_accounts=ip_accounts,
            instrument_accounts=instrument_accounts,
            beneficiary_senders=beneficiary_senders,
            beneficiary_payments=beneficiary_payments,
            beneficiary_amount=beneficiary_amount,
        )
        return result

    async def health(self) -> bool:
        try:
            await asyncio.wait_for(self.driver.verify_connectivity(), timeout=1.5)
            return True
        except Exception:
            return False


def relationship_engine(
    request: RiskRequest,
    *,
    device_accounts: int,
    ip_accounts: int,
    instrument_accounts: int,
    beneficiary_senders: int,
    beneficiary_payments: int,
    beneficiary_amount: float,
) -> EngineResult:
    """Score graph evidence with shared-network false-positive safeguards."""
    device_risk = clamp(max(0, device_accounts - 1) / 4)
    instrument_risk = clamp(max(0, instrument_accounts - 1) / 3)
    # High fan-in is expected for merchants. Treat it as peer-beneficiary risk
    # only when the payment is not classified as a merchant purchase.
    peer_beneficiary = request.merchant_category is None
    beneficiary_risk = clamp(max(0, beneficiary_senders - 2) / 4) if peer_beneficiary else 0.0
    ip_type = str(request.context.get("ipType", "")).upper()
    suspicious_network = ip_type in {"DATACENTER", "PROXY", "VPN"}
    # Shared IP is weak evidence by itself: homes, offices, campuses and mobile
    # carrier NAT legitimately put many customers behind one address.
    ip_cap = 0.7 if suspicious_network else 0.45
    ip_risk = min(ip_cap, clamp(max(0, ip_accounts - 3) / 12))

    split_sources = (
        peer_beneficiary
        and beneficiary_senders >= 4
        and beneficiary_payments >= 5
        and beneficiary_amount >= 20_000
        and beneficiary_amount / beneficiary_payments <= 10_000
    )
    splitting_risk = 0.82 if split_sources else 0.0
    strong = [
        value
        for value in (device_risk, instrument_risk, beneficiary_risk, splitting_risk)
        if value >= 0.45
    ]
    corroboration_bonus = 0.12 if len(strong) >= 2 else 0.0
    score = clamp(
        max(device_risk, instrument_risk, beneficiary_risk, splitting_risk, ip_risk)
        + corroboration_bonus
    )
    signals = []
    if device_accounts >= 3:
        signals.append(
            RiskSignal(
                type="SHARED_DEVICE",
                source="GRAPH",
                score=device_risk,
                description="Multiple sender accounts are linked to the same device.",
                evidence={"deviceId": request.device_id, "linkedAccounts": device_accounts},
            )
        )
    if ip_accounts >= 8:
        signals.append(
            RiskSignal(
                type="SHARED_NETWORK",
                source="GRAPH",
                score=ip_risk,
                description="Multiple sender accounts originate from the same network address.",
                evidence={"ipAddress": request.ip_address, "linkedAccounts": ip_accounts},
            )
        )
    if instrument_accounts >= 3:
        signals.append(
            RiskSignal(
                type="SHARED_PAYMENT_INSTRUMENT",
                source="GRAPH",
                score=instrument_risk,
                description="Multiple sender accounts use the same payment instrument.",
                evidence={
                    "paymentInstrumentId": request.payment_instrument_id,
                    "linkedAccounts": instrument_accounts,
                },
            )
        )
    if peer_beneficiary and beneficiary_senders >= 4:
        signals.append(
            RiskSignal(
                type="MULE_FAN_IN",
                source="GRAPH",
                score=beneficiary_risk,
                description="Many sender accounts converge on the same beneficiary.",
                evidence={
                    "receiverId": request.receiver_id,
                    "uniqueSenders": beneficiary_senders,
                },
            )
        )
    if split_sources:
        signals.append(
            RiskSignal(
                type="MULTI_SOURCE_AMOUNT_SPLITTING",
                source="GRAPH",
                score=splitting_risk,
                description=(
                    "Multiple senders split a material total into smaller payments "
                    "to one beneficiary."
                ),
                evidence={
                    "receiverId": request.receiver_id,
                    "uniqueSenders": beneficiary_senders,
                    "paymentCount": beneficiary_payments,
                    "aggregateAmount": round(beneficiary_amount, 2),
                },
            )
        )
    return EngineResult(
        score=score,
        signals=signals,
        metadata={
            "deviceAccounts7d": device_accounts,
            "ipAccounts24h": ip_accounts,
            "instrumentAccounts7d": instrument_accounts,
            "beneficiarySenders1h": beneficiary_senders,
            "beneficiaryPayments1h": beneficiary_payments,
            "beneficiaryAmount1h": round(beneficiary_amount, 2),
            "corroborated": len(strong) >= 2,
        },
    )


class QdrantSimilarityStore:
    def __init__(
        self,
        *,
        url: str,
        api_key: str | None,
        embedder: HashingEmbedder,
        timeout: float,
        threshold: float,
    ) -> None:
        self.url = url.rstrip("/")
        self.embedder = embedder
        self.threshold = threshold
        self.client = httpx.AsyncClient(
            timeout=timeout, headers={"api-key": api_key} if api_key else None
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def analyze(self, request: RiskRequest, context: str) -> EngineResult:
        del request
        try:
            response = await self.client.post(
                f"{self.url}/collections/risk_case_memory/points/search",
                json={
                    "vector": self.embedder.embed(context),
                    "limit": 5,
                    "score_threshold": self.threshold,
                    "with_payload": True,
                    "with_vector": False,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("Similarity analysis unavailable: %s", error)
            return EngineResult(score=0, available=False)
        matches = response.json().get("result", [])
        abuse_matches = [
            item
            for item in matches
            if (item.get("payload") or {}).get("final_label") == "CONFIRMED_ABUSE"
        ]
        score = max((float(item.get("score", 0)) for item in abuse_matches), default=0.0)
        signals = []
        if score >= 0.55:
            best = max(abuse_matches, key=lambda item: float(item.get("score", 0)))
            payload = best.get("payload") or {}
            signals.append(
                RiskSignal(
                    type="SIMILAR_CONFIRMED_CASE",
                    source="SIMILARITY",
                    score=clamp(score),
                    description="Current behavior resembles a resolved confirmed-abuse case.",
                    evidence={"caseId": payload.get("reference_id"), "similarity": round(score, 4)},
                )
            )
        return EngineResult(
            score=clamp(score), signals=signals, metadata={"matchCount": len(matches)}
        )

    async def health(self) -> bool:
        try:
            return (await self.client.get(f"{self.url}/healthz")).is_success
        except httpx.HTTPError:
            return False


class HttpVerificationClient:
    def __init__(self, url: str, api_key: str | None, timeout: float) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=timeout, headers={"X-API-Key": api_key} if api_key else None
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def verify(
        self,
        request: RiskRequest,
        *,
        decision: Decision,
        recommendation: str,
        confidence: float,
        dimensions: dict[str, float],
        signals: list[RiskSignal],
        summary: str,
    ) -> tuple[Decision, str, float, list[RiskSignal]]:
        payload = {
            "transaction_id": request.transaction_id,
            "account_id": request.sender_id,
            "proposed_decision": decision.value,
            "proposed_recommendation": recommendation,
            "confidence": confidence,
            "dimensions": dimensions,
            "signals": [signal.model_dump() for signal in signals],
            "summary": summary,
            "context": {"receiverId": request.receiver_id},
        }
        try:
            response = await self.client.post(f"{self.url}/api/v1/verify", json=payload)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as error:
            raise RequiredDependencyError("AI risk verifier is unavailable") from error
        verifier_signal = RiskSignal(
            type="AI_VERIFICATION",
            source="VERIFIER",
            score=float(body["confidence"]),
            description=body["rationale"],
            evidence={
                "traceId": body["trace_id"],
                "accepted": body["accepted"],
                "reasonCodes": body["reason_codes"],
                "references": [item["reference_id"] for item in body.get("evidence", [])],
            },
        )
        return (
            Decision(body["final_decision"]),
            str(body["recommendation"]),
            float(body["confidence"]),
            [verifier_signal],
        )

    async def health(self) -> bool:
        try:
            return (await self.client.get(f"{self.url}/health/live")).is_success
        except httpx.HTTPError:
            return False
