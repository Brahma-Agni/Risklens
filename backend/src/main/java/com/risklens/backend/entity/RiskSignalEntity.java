package com.risklens.backend.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
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
@Table(name = "risk_signals")
@Getter
@Setter
@NoArgsConstructor
public class RiskSignalEntity {

    @Id
    @GeneratedValue
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "risk_case_id", nullable = false)
    private RiskCaseEntity riskCase;

    @Column(name = "signal_type", nullable = false, length = 64)
    private String signalType;

    @Column(name = "source_engine", nullable = false, length = 32)
    private String sourceEngine;

    @Column(precision = 5, scale = 4)
    private BigDecimal score;

    @Column(nullable = false)
    private String description;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private String evidence;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
}

