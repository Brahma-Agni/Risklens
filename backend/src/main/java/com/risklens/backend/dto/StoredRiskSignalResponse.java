package com.risklens.backend.dto;

import java.math.BigDecimal;
import java.time.Instant;

public record StoredRiskSignalResponse(
        String type,
        String source,
        BigDecimal score,
        String description,
        String evidence,
        Instant createdAt
) {
}

