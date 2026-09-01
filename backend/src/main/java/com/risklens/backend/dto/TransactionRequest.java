package com.risklens.backend.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

public record TransactionRequest(
        @NotBlank @Size(max = 64) String transactionId,
        @NotBlank @Size(max = 64) String senderId,
        @NotBlank @Size(max = 64) String receiverId,
        @NotNull @DecimalMin(value = "0.01") @Digits(integer = 16, fraction = 2)
        BigDecimal amount,
        @NotBlank @Pattern(regexp = "[A-Z]{3}") String currency,
        @Size(max = 128) String deviceId,
        @Pattern(
                regexp = "^[0-9a-fA-F:.]+$",
                message = "must be an IPv4 or IPv6 address")
        String ipAddress,
        @NotBlank @Size(max = 32) String paymentMethod,
        @NotNull Instant timestamp,
        @Size(max = 128) String ipId,
        @Size(max = 128) String paymentInstrumentId,
        @Size(max = 128) String locationCity,
        @Size(max = 128) String locationState,
        @Pattern(regexp = "[A-Z]{2}") String locationCountry,
        @Size(max = 32) String authorizationStatus,
        @Size(max = 32) String authenticationStatus,
        @Size(max = 32) String transactionStatus,
        @Size(max = 64) String failureReason,
        @Size(max = 64) String merchantCategory,
        @Size(max = 32) Map<String, Object> context
) {
}
