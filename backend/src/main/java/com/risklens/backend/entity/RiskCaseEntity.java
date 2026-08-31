package com.risklens.backend.entity;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "risk_cases")
@Getter
@Setter
@NoArgsConstructor
public class RiskCaseEntity {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "case_id", nullable = false, unique = true, length = 64)
    private String caseId;

    @Column(name = "transaction_id", nullable = false, length = 64)
    private String transactionId;

    @Column(name = "account_id", nullable = false, length = 64)
    private String accountId;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false, columnDefinition = "risk_case_status")
    private RiskCaseStatus status;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false, columnDefinition = "risk_severity")
    private RiskSeverity severity;

    @Column(name = "transaction_risk", precision = 5, scale = 4)
    private BigDecimal transactionRisk;

    @Column(name = "account_risk", precision = 5, scale = 4)
    private BigDecimal accountRisk;

    @Column(name = "behavior_risk", precision = 5, scale = 4)
    private BigDecimal behaviorRisk;

    @Column(name = "temporal_risk", precision = 5, scale = 4)
    private BigDecimal temporalRisk;

    @Column(name = "structural_risk", precision = 5, scale = 4)
    private BigDecimal structuralRisk;

    @Column(name = "similarity_risk", precision = 5, scale = 4)
    private BigDecimal similarityRisk;

    @Column(name = "ring_risk", precision = 5, scale = 4)
    private BigDecimal ringRisk;

    @Column(precision = 5, scale = 4)
    private BigDecimal confidence;

    @Column(length = 64)
    private String recommendation;

    @Column(name = "ai_summary")
    private String aiSummary;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Column(name = "resolved_at")
    private Instant resolvedAt;
}

