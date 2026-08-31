package com.risklens.backend.dto;

import java.math.BigDecimal;
import java.util.List;

public record RiskEvaluationResponse(
        BigDecimal transactionRisk,
        BigDecimal accountRisk,
        BigDecimal behaviorRisk,
        BigDecimal temporalRisk,
        BigDecimal structuralRisk,
        BigDecimal similarityRisk,
        BigDecimal ringRisk,
        BigDecimal confidence,
        String decision,
        String recommendation,
        String summary,
        List<RiskSignalResponse> signals
) {
}

