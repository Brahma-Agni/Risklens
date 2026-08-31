package com.risklens.backend.client;

import com.risklens.backend.dto.RiskEvaluationRequest;
import com.risklens.backend.dto.RiskEvaluationResponse;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
@RequiredArgsConstructor
@Slf4j
public class RiskServiceClient {

    private final RestClient riskRestClient;

    public Optional<RiskEvaluationResponse> evaluate(RiskEvaluationRequest request) {
        try {
            RiskEvaluationResponse response = riskRestClient.post()
                    .uri("/api/v1/risk/evaluate")
                    .body(request)
                    .retrieve()
                    .body(RiskEvaluationResponse.class);
            return Optional.ofNullable(response);
        } catch (RestClientException exception) {
            log.warn("Risk service evaluation failed: {}", exception.getMessage());
            return Optional.empty();
        }
    }
}

