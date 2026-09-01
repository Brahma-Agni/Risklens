package com.risklens.backend.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

public record RiskEvaluationRequest(
        String transactionId,
        String senderId,
        String receiverId,
        BigDecimal amount,
        String currency,
        String deviceId,
        String ipAddress,
        String paymentMethod,
        Instant timestamp,
        String ipId,
        String paymentInstrumentId,
        String locationCity,
        String locationState,
        String locationCountry,
        String authorizationStatus,
        String authenticationStatus,
        String transactionStatus,
        String failureReason,
        String merchantCategory,
        Map<String, Object> context
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
                request.timestamp(),
                request.ipId(),
                request.paymentInstrumentId(),
                request.locationCity(),
                request.locationState(),
                request.locationCountry(),
                request.authorizationStatus(),
                request.authenticationStatus(),
                request.transactionStatus(),
                request.failureReason(),
                request.merchantCategory(),
                request.context());
    }
}
