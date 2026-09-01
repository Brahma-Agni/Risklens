package com.risklens.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import com.risklens.backend.entity.RiskCaseEntity;
import com.risklens.backend.repository.AnalystDecisionRepository;
import com.risklens.backend.repository.RiskCaseRepository;
import com.risklens.backend.repository.RiskSignalRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class RiskCaseServiceTest {

    @Mock
    private RiskCaseRepository riskCaseRepository;
    @Mock
    private RiskSignalRepository riskSignalRepository;
    @Mock
    private AnalystDecisionRepository analystDecisionRepository;

    private RiskCaseService riskCaseService;

    @BeforeEach
    void setUp() {
        riskCaseService = new RiskCaseService(
                riskCaseRepository,
                riskSignalRepository,
                analystDecisionRepository,
                new ObjectMapper());
        ReflectionTestUtils.setField(
                riskCaseService, "reviewThreshold", new BigDecimal("0.75"));
    }

    @Test
    void dashboardQueryReturnsOnlyRepositoryFilteredHighRiskLinkedCases() {
        RiskCaseEntity riskCase = new RiskCaseEntity();
        riskCase.setCaseId("CASE-HIGH-LINKED");
        riskCase.setTransactionId("TX-HIGH-LINKED");
        riskCase.setAccountId("USER-001");
        riskCase.setStatus(RiskCaseStatus.OPEN);
        riskCase.setSeverity(RiskSeverity.HIGH);
        riskCase.setRingRisk(new BigDecimal("0.82"));
        riskCase.setConfidence(new BigDecimal("0.91"));
        riskCase.setCreatedAt(Instant.parse("2026-08-31T00:00:00Z"));
        when(riskCaseRepository
                        .findByStatusInAndRingRiskGreaterThanEqualOrderByRingRiskDescCreatedAtDesc(
                                eq(List.of(RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW)),
                                eq(new BigDecimal("0.75")),
                                any(Pageable.class)))
                .thenReturn(List.of(riskCase));

        var result = riskCaseService.listHighRiskLinked(100);

        assertThat(result).hasSize(1);
        assertThat(result.get(0).caseId()).isEqualTo("CASE-HIGH-LINKED");
        assertThat(result.get(0).ringRisk()).isEqualByComparingTo("0.82");
        verify(riskCaseRepository)
                .findByStatusInAndRingRiskGreaterThanEqualOrderByRingRiskDescCreatedAtDesc(
                        eq(List.of(RiskCaseStatus.OPEN, RiskCaseStatus.IN_REVIEW)),
                        eq(new BigDecimal("0.75")),
                        any(Pageable.class));
    }
}
