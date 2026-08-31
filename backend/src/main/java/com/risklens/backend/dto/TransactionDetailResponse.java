package com.risklens.backend.dto;

import com.risklens.backend.domain.TransactionStatus;
import java.math.BigDecimal;
import java.time.Instant;

public record TransactionDetailResponse(
        String transactionId,
        String senderId,
        String receiverId,
        BigDecimal amount,
        String currency,
        String deviceId,
        String ipAddress,
        String paymentMethod,
        Instant timestamp,
        Instant receivedAt,
        TransactionStatus status,
        BigDecimal riskScore,
        String caseId
) {
}

