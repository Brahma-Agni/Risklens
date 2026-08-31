package com.risklens.backend.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "risklens.risk-service")
public record RiskClientProperties(
        String baseUrl,
        Duration connectTimeout,
        Duration readTimeout
) {
}

