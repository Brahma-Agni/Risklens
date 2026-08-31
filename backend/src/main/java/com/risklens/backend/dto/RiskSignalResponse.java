package com.risklens.backend.dto;

import java.math.BigDecimal;
import java.util.Map;

public record RiskSignalResponse(
        String type,
        String source,
        BigDecimal score,
        String description,
        Map<String, Object> evidence
) {
}

