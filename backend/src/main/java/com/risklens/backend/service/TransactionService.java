package com.risklens.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.risklens.backend.client.RiskServiceClient;
import com.risklens.backend.domain.TransactionStatus;
import com.risklens.backend.dto.RiskEvaluationRequest;
import com.risklens.backend.dto.RiskEvaluationResponse;
import com.risklens.backend.dto.TransactionDetailResponse;
import com.risklens.backend.dto.TransactionRequest;
import com.risklens.backend.dto.TransactionResponse;
import com.risklens.backend.entity.RiskCaseEntity;
import com.risklens.backend.entity.TransactionEntity;
import com.risklens.backend.exception.ConflictException;
import com.risklens.backend.exception.ResourceNotFoundException;
import com.risklens.backend.repository.RiskCaseRepository;
import com.risklens.backend.repository.TransactionRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class TransactionService {

    private final TransactionRepository transactionRepository;
    private final RiskCaseRepository riskCaseRepository;
    private final RiskServiceClient riskServiceClient;
    private final RiskCaseService riskCaseService;
    private final ObjectMapper objectMapper;

    @Value("${risklens.review-threshold}")
    private BigDecimal reviewThreshold;

    public TransactionResponse process(TransactionRequest request) {
        if (transactionRepository.existsByTransactionId(request.transactionId())) {
            throw new ConflictException(
                    "Transaction already exists: " + request.transactionId());
        }

        TransactionEntity transaction = transactionRepository.save(toEntity(request));
        Optional<RiskEvaluationResponse> evaluation = riskServiceClient.evaluate(
                RiskEvaluationRequest.from(request));

        if (evaluation.isEmpty()) {
            transaction.setStatus(TransactionStatus.RISK_UNAVAILABLE);
            transactionRepository.save(transaction);
            return new TransactionResponse(
                    transaction.getTransactionId(),
                    transaction.getStatus(),
                    TransactionStatus.REVIEW.name(),
                    null,
                    null,
                    false);
        }

        RiskEvaluationResponse risk = evaluation.get();
        BigDecimal riskScore = overallRisk(risk);
        TransactionStatus status = mapDecision(risk.decision(), riskScore);
        transaction.setRiskScore(riskScore);
        transaction.setStatus(status);
        transactionRepository.save(transaction);

        RiskCaseEntity riskCase = null;
        if (requiresCase(status, riskScore)) {
            riskCase = riskCaseService.createCase(transaction, risk);
        }

        return new TransactionResponse(
                transaction.getTransactionId(),
                status,
                status.name(),
                riskScore,
                riskCase == null ? null : riskCase.getCaseId(),
                true);
    }

    @Transactional(readOnly = true)
    public TransactionDetailResponse get(String transactionId) {
        TransactionEntity transaction = transactionRepository.findByTransactionId(transactionId)
                .orElseThrow(() -> new ResourceNotFoundException(
                        "Transaction not found: " + transactionId));
        return toDetail(transaction);
    }

    @Transactional(readOnly = true)
    public List<TransactionDetailResponse> recent(int limit) {
        return transactionRepository.findAllByOrderByOccurredAtDesc(PageRequest.of(0, limit))
                .stream()
                .map(this::toDetail)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<TransactionDetailResponse> forAccount(String accountId, int limit) {
        return transactionRepository.findBySenderAccountIdOrderByOccurredAtDesc(
                        accountId, PageRequest.of(0, limit))
                .stream()
                .map(this::toDetail)
                .toList();
    }

    private TransactionEntity toEntity(TransactionRequest request) {
        TransactionEntity transaction = new TransactionEntity();
        transaction.setTransactionId(request.transactionId());
        transaction.setSenderAccountId(request.senderId());
        transaction.setReceiverId(request.receiverId());
        transaction.setAmount(request.amount());
        transaction.setCurrency(request.currency().toUpperCase(Locale.ROOT));
        transaction.setDeviceId(request.deviceId());
        transaction.setIpAddress(request.ipAddress());
        transaction.setPaymentMethod(request.paymentMethod().toUpperCase(Locale.ROOT));
        transaction.setOccurredAt(request.timestamp());
        transaction.setReceivedAt(Instant.now());
        transaction.setStatus(TransactionStatus.PENDING);
        try {
            transaction.setRawPayload(objectMapper.writeValueAsString(request));
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Transaction payload could not be serialized", exception);
        }
        return transaction;
    }

    private TransactionDetailResponse toDetail(TransactionEntity transaction) {
        String caseId = riskCaseRepository.findByTransactionId(transaction.getTransactionId())
                .map(RiskCaseEntity::getCaseId)
                .orElse(null);
        return new TransactionDetailResponse(
                transaction.getTransactionId(),
                transaction.getSenderAccountId(),
                transaction.getReceiverId(),
                transaction.getAmount(),
                transaction.getCurrency(),
                transaction.getDeviceId(),
                transaction.getIpAddress(),
                transaction.getPaymentMethod(),
                transaction.getOccurredAt(),
                transaction.getReceivedAt(),
                transaction.getStatus(),
                transaction.getRiskScore(),
                caseId);
    }

    private BigDecimal overallRisk(RiskEvaluationResponse risk) {
        return java.util.stream.Stream.of(
                        risk.transactionRisk(),
                        risk.accountRisk(),
                        risk.ringRisk())
                .filter(value -> value != null)
                .max(BigDecimal::compareTo)
                .orElse(BigDecimal.ZERO)
                .max(BigDecimal.ZERO)
                .min(BigDecimal.ONE)
                .setScale(4, RoundingMode.HALF_UP);
    }

    private TransactionStatus mapDecision(String decision, BigDecimal riskScore) {
        if (decision != null) {
            try {
                TransactionStatus parsed = TransactionStatus.valueOf(
                        decision.toUpperCase(Locale.ROOT));
                if (parsed != TransactionStatus.PENDING
                        && parsed != TransactionStatus.RISK_UNAVAILABLE) {
                    return parsed;
                }
            } catch (IllegalArgumentException ignored) {
                // Fall through to deterministic threshold behavior.
            }
        }
        return riskScore.compareTo(reviewThreshold) >= 0
                ? TransactionStatus.REVIEW
                : TransactionStatus.ALLOW;
    }

    private boolean requiresCase(TransactionStatus status, BigDecimal riskScore) {
        return status == TransactionStatus.REVIEW
                || status == TransactionStatus.HOLD
                || status == TransactionStatus.DECLINED
                || riskScore.compareTo(reviewThreshold) >= 0;
    }
}

