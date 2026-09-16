import logging

import httpx

from .models import CaseMemoryRequest, RiskEvaluation, TransactionRequest

logger = logging.getLogger(__name__)


class RiskClients:
    def __init__(
        self,
        risk_service_url: str,
        verifier_url: str,
        timeout: float,
        verifier_api_key: str = "",
    ) -> None:
        self.risk_service_url = risk_service_url.rstrip("/")
        self.verifier_url = verifier_url.rstrip("/")
        self.verifier_api_key = verifier_api_key
        self.client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self.client.close()

    def health(self) -> bool:
        try:
            return self.client.get(f"{self.risk_service_url}/health/live").is_success
        except httpx.HTTPError:
            return False

    def evaluate(self, payload: TransactionRequest) -> RiskEvaluation | None:
        try:
            response = self.client.post(
                f"{self.risk_service_url}/api/v1/risk/evaluate",
                json=payload.model_dump(mode="json", by_alias=True),
            )
            response.raise_for_status()
            return RiskEvaluation.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Risk evaluation unavailable: %s", error)
            return None

    def store_memory(self, payload: CaseMemoryRequest) -> None:
        headers = {"X-API-Key": self.verifier_api_key} if self.verifier_api_key else {}
        try:
            response = self.client.post(
                f"{self.verifier_url}/api/v1/memory/cases",
                json=payload.model_dump(mode="json"),
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning(
                "Reviewed case memory indexing deferred for %s: %s",
                payload.risk_case_id,
                error,
            )
