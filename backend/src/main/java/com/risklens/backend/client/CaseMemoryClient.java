package com.risklens.backend.client;

import com.risklens.backend.dto.CaseMemoryRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
@Slf4j
public class CaseMemoryClient {

    private final RestClient verifierRestClient;

    public CaseMemoryClient(@Qualifier("verifierRestClient") RestClient verifierRestClient) {
        this.verifierRestClient = verifierRestClient;
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void index(com.risklens.backend.service.CaseMemoryEvent event) {
        CaseMemoryRequest request = event.request();
        try {
            verifierRestClient.post()
                    .uri("/api/v1/memory/cases")
                    .body(request)
                    .retrieve()
                    .toBodilessEntity();
            log.info("Indexed reviewed risk case in Qdrant memory: {}", request.riskCaseId());
        } catch (RestClientException exception) {
            // The analyst decision is already committed. A verifier outage must not
            // make the staff workflow appear to have failed.
            log.warn("Reviewed case memory indexing deferred for {}: {}",
                    request.riskCaseId(), exception.getMessage());
        }
    }
}
