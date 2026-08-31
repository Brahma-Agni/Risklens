package com.risklens.backend.dto;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record RiskCaseDetailResponse(
        String caseId,
        String transactionId,
        String accountId,
        RiskCaseStatus status,
        RiskSeverity severity,
        BigDecimal transactionRisk,
        BigDecimal accountRisk,
        BigDecimal behaviorRisk,
        BigDecimal temporalRisk,
        BigDecimal structuralRisk,
        BigDecimal similarityRisk,
        BigDecimal ringRisk,
        BigDecimal confidence,
        String recommendation,
        String aiSummary,
        Instant createdAt,
        Instant updatedAt,
        Instant resolvedAt,
        List<StoredRiskSignalResponse> signals,
        List<AnalystDecisionResponse> decisions
) {
}

