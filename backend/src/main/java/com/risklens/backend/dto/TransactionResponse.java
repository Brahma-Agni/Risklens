package com.risklens.backend.dto;

import com.risklens.backend.domain.TransactionStatus;
import java.math.BigDecimal;

public record TransactionResponse(
        String transactionId,
        TransactionStatus status,
        String recommendedAction,
        BigDecimal riskScore,
        String caseId,
        boolean riskServiceAvailable
) {
}

