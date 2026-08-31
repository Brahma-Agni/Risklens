package com.risklens.backend.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record RiskEvaluationRequest(
        String transactionId,
        String senderId,
        String receiverId,
        BigDecimal amount,
        String currency,
        String deviceId,
        String ipAddress,
        String paymentMethod,
        Instant timestamp
) {
    public static RiskEvaluationRequest from(TransactionRequest request) {
        return new RiskEvaluationRequest(
                request.transactionId(),
                request.senderId(),
                request.receiverId(),
                request.amount(),
                request.currency(),
                request.deviceId(),
                request.ipAddress(),
                request.paymentMethod(),
                request.timestamp());
    }
}

