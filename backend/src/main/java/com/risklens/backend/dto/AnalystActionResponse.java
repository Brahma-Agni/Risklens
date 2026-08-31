package com.risklens.backend.dto;

import com.risklens.backend.domain.AnalystDecisionType;
import java.time.Instant;
import java.util.UUID;

public record AnalystActionResponse(
        UUID id,
        String caseId,
        String transactionId,
        String accountId,
        AnalystDecisionType decision,
        String analyst,
        String comment,
        Instant createdAt
) {
}
