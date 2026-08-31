package com.risklens.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.risklens.backend.client.RiskServiceClient;
import com.risklens.backend.domain.TransactionStatus;
import com.risklens.backend.dto.RiskEvaluationResponse;
import com.risklens.backend.dto.TransactionRequest;
import com.risklens.backend.entity.RiskCaseEntity;
import com.risklens.backend.entity.TransactionEntity;
import com.risklens.backend.exception.ConflictException;
import com.risklens.backend.repository.RiskCaseRepository;
import com.risklens.backend.repository.TransactionRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class TransactionServiceTest {

    @Mock
    private TransactionRepository transactionRepository;
    @Mock
    private RiskCaseRepository riskCaseRepository;
    @Mock
    private RiskServiceClient riskServiceClient;
    @Mock
    private RiskCaseService riskCaseService;

    private TransactionService transactionService;

    @BeforeEach
    void setUp() {
        ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
        transactionService = new TransactionService(
                transactionRepository,
                riskCaseRepository,
                riskServiceClient,
                riskCaseService,
                objectMapper);
        ReflectionTestUtils.setField(
                transactionService, "reviewThreshold", new BigDecimal("0.70"));
    }

    @Test
    void returnsReviewFallbackWhenRiskServiceIsUnavailable() {
        TransactionRequest request = request("TX-UNAVAILABLE");
        saveReturnsInput();
        when(riskServiceClient.evaluate(any())).thenReturn(Optional.empty());

        var response = transactionService.process(request);

        assertThat(response.status()).isEqualTo(TransactionStatus.RISK_UNAVAILABLE);
        assertThat(response.recommendedAction()).isEqualTo("REVIEW");
        assertThat(response.riskServiceAvailable()).isFalse();
        verify(transactionRepository, times(2)).save(any(TransactionEntity.class));
        verify(riskCaseService, never()).createCase(any(), any());
    }

    @Test
    void createsRiskCaseForHighRiskEvaluation() {
        TransactionRequest request = request("TX-HIGH-RISK");
        saveReturnsInput();
        var evaluation = new RiskEvaluationResponse(
                new BigDecimal("0.82"),
                new BigDecimal("0.76"),
                new BigDecimal("0.71"),
                new BigDecimal("0.88"),
                new BigDecimal("0.90"),
                new BigDecimal("0.87"),
                new BigDecimal("0.93"),
                new BigDecimal("0.91"),
                "REVIEW",
                "HOLD_AND_VERIFY",
                "Coordinated activity detected",
                List.of());
        when(riskServiceClient.evaluate(any())).thenReturn(Optional.of(evaluation));
        RiskCaseEntity riskCase = new RiskCaseEntity();
        riskCase.setCaseId("CASE-TEST");
        when(riskCaseService.createCase(any(), any())).thenReturn(riskCase);

        var response = transactionService.process(request);

        assertThat(response.status()).isEqualTo(TransactionStatus.REVIEW);
        assertThat(response.riskScore()).isEqualByComparingTo("0.9300");
        assertThat(response.caseId()).isEqualTo("CASE-TEST");
        assertThat(response.riskServiceAvailable()).isTrue();
    }

    @Test
    void rejectsDuplicateTransactionId() {
        TransactionRequest request = request("TX-DUPLICATE");
        when(transactionRepository.existsByTransactionId("TX-DUPLICATE"))
                .thenReturn(true);

        assertThatThrownBy(() -> transactionService.process(request))
                .isInstanceOf(ConflictException.class)
                .hasMessageContaining("TX-DUPLICATE");

        verify(transactionRepository, never()).save(any());
    }

    private TransactionRequest request(String transactionId) {
        return new TransactionRequest(
                transactionId,
                "USER-DEMO-001",
                "MERCHANT-DEMO-001",
                new BigDecimal("7800.00"),
                "INR",
                "DEVICE-001",
                "10.24.81.19",
                "UPI",
                Instant.parse("2026-08-30T12:05:32Z"));
    }

    private void saveReturnsInput() {
        when(transactionRepository.save(any(TransactionEntity.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));
    }
}
