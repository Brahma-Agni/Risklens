package com.risklens.backend.dto;

import com.risklens.backend.domain.TransactionStatus;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

public record TransactionDetailResponse(
        String transactionId,
        String senderId,
        String receiverId,
        BigDecimal amount,
        String currency,
        String deviceId,
        String ipAddress,
        String paymentMethod,
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
        Map<String, Object> context,
        Instant timestamp,
        Instant receivedAt,
        TransactionStatus status,
        BigDecimal riskScore,
        String caseId
) {
}
