package com.risklens.backend.dto;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import java.math.BigDecimal;
import java.time.Instant;

public record RiskCaseSummaryResponse(
        String caseId,
        String transactionId,
        String accountId,
        RiskCaseStatus status,
        RiskSeverity severity,
        BigDecimal ringRisk,
        BigDecimal confidence,
        String recommendation,
        Instant createdAt
) {
}

