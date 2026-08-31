package com.risklens.backend.entity;

import com.risklens.backend.domain.AnalystDecisionType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "analyst_decisions")
@Getter
@Setter
@NoArgsConstructor
public class AnalystDecisionEntity {

    @Id
    @GeneratedValue
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "risk_case_id", nullable = false)
    private RiskCaseEntity riskCase;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false, columnDefinition = "analyst_decision_type")
    private AnalystDecisionType decision;

    @Column(name = "analyst_id", nullable = false, length = 128)
    private String analystId;

    @Column
    private String comment;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
}

