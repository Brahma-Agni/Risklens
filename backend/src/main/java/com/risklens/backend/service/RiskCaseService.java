package com.risklens.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import com.risklens.backend.dto.AnalystDecisionResponse;
import com.risklens.backend.dto.RiskCaseDetailResponse;
import com.risklens.backend.dto.RiskCaseSummaryResponse;
import com.risklens.backend.dto.RiskEvaluationResponse;
import com.risklens.backend.dto.RiskSignalResponse;
import com.risklens.backend.dto.StoredRiskSignalResponse;
import com.risklens.backend.entity.RiskCaseEntity;
import com.risklens.backend.entity.RiskSignalEntity;
import com.risklens.backend.entity.TransactionEntity;
import com.risklens.backend.exception.ResourceNotFoundException;
import com.risklens.backend.repository.AnalystDecisionRepository;
import com.risklens.backend.repository.RiskCaseRepository;
import com.risklens.backend.repository.RiskSignalRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class RiskCaseService {

    private static final String EMPTY_JSON = "{}";

    private final RiskCaseRepository riskCaseRepository;
    private final RiskSignalRepository riskSignalRepository;
    private final AnalystDecisionRepository analystDecisionRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public RiskCaseEntity createCase(
            TransactionEntity transaction, RiskEvaluationResponse evaluation) {
        Instant now = Instant.now();
        RiskCaseEntity riskCase = new RiskCaseEntity();
        riskCase.setCaseId("CASE-" + UUID.randomUUID().toString().substring(0, 12).toUpperCase(Locale.ROOT));
        riskCase.setTransactionId(transaction.getTransactionId());
        riskCase.setAccountId(transaction.getSenderAccountId());
        riskCase.setStatus(RiskCaseStatus.OPEN);
        riskCase.setSeverity(severityFor(maxRisk(evaluation)));
        riskCase.setTransactionRisk(evaluation.transactionRisk());
        riskCase.setAccountRisk(evaluation.accountRisk());
        riskCase.setBehaviorRisk(evaluation.behaviorRisk());
        riskCase.setTemporalRisk(evaluation.temporalRisk());
        riskCase.setStructuralRisk(evaluation.structuralRisk());
        riskCase.setSimilarityRisk(evaluation.similarityRisk());
        riskCase.setRingRisk(evaluation.ringRisk());
        riskCase.setConfidence(evaluation.confidence());
        riskCase.setRecommendation(evaluation.recommendation());
        riskCase.setAiSummary(evaluation.summary());
        riskCase.setCreatedAt(now);
        riskCase.setUpdatedAt(now);
        RiskCaseEntity savedCase = riskCaseRepository.save(riskCase);

        if (evaluation.signals() != null) {
            evaluation.signals().stream()
                    .map(signal -> toEntity(savedCase, signal, now))
                    .forEach(riskSignalRepository::save);
        }
        return savedCase;
    }

    @Transactional(readOnly = true)
    public List<RiskCaseSummaryResponse> list(
            RiskCaseStatus status, RiskSeverity severity, int limit) {
        var pageable = PageRequest.of(0, limit);
        List<RiskCaseEntity> cases;
        if (status != null && severity != null) {
            cases = riskCaseRepository.findByStatusAndSeverityOrderByCreatedAtDesc(
                    status, severity, pageable);
        } else if (status != null) {
            cases = riskCaseRepository.findByStatusOrderByCreatedAtDesc(status, pageable);
        } else if (severity != null) {
            cases = riskCaseRepository.findBySeverityOrderByCreatedAtDesc(severity, pageable);
        } else {
            cases = riskCaseRepository.findAllByOrderByCreatedAtDesc(pageable);
        }
        return cases.stream().map(this::toSummary).toList();
    }

    @Transactional(readOnly = true)
    public RiskCaseDetailResponse get(String caseId) {
        RiskCaseEntity riskCase = findEntity(caseId);
        List<StoredRiskSignalResponse> signals = riskSignalRepository
                .findByRiskCaseIdOrderByCreatedAtAsc(riskCase.getId())
                .stream()
                .map(signal -> new StoredRiskSignalResponse(
                        signal.getSignalType(),
                        signal.getSourceEngine(),
                        signal.getScore(),
                        signal.getDescription(),
                        signal.getEvidence(),
                        signal.getCreatedAt()))
                .toList();
        List<AnalystDecisionResponse> decisions = analystDecisionRepository
                .findByRiskCaseIdOrderByCreatedAtDesc(riskCase.getId())
                .stream()
                .map(decision -> new AnalystDecisionResponse(
                        decision.getId(),
                        decision.getDecision(),
                        decision.getAnalystId(),
                        decision.getComment(),
                        decision.getCreatedAt()))
                .toList();

        return new RiskCaseDetailResponse(
                riskCase.getCaseId(),
                riskCase.getTransactionId(),
                riskCase.getAccountId(),
                riskCase.getStatus(),
                riskCase.getSeverity(),
                riskCase.getTransactionRisk(),
                riskCase.getAccountRisk(),
                riskCase.getBehaviorRisk(),
                riskCase.getTemporalRisk(),
                riskCase.getStructuralRisk(),
                riskCase.getSimilarityRisk(),
                riskCase.getRingRisk(),
                riskCase.getConfidence(),
                riskCase.getRecommendation(),
                riskCase.getAiSummary(),
                riskCase.getCreatedAt(),
                riskCase.getUpdatedAt(),
                riskCase.getResolvedAt(),
                signals,
                decisions);
    }

    @Transactional(readOnly = true)
    public RiskCaseEntity findEntity(String caseId) {
        return riskCaseRepository.findByCaseId(caseId)
                .orElseThrow(() -> new ResourceNotFoundException(
                        "Risk case not found: " + caseId));
    }

    private RiskSignalEntity toEntity(
            RiskCaseEntity riskCase, RiskSignalResponse signal, Instant createdAt) {
        RiskSignalEntity entity = new RiskSignalEntity();
        entity.setRiskCase(riskCase);
        entity.setSignalType(defaultText(signal.type(), "UNKNOWN"));
        entity.setSourceEngine(defaultText(signal.source(), "RISK_SERVICE"));
        entity.setScore(signal.score());
        entity.setDescription(defaultText(signal.description(), "Risk signal detected"));
        entity.setEvidence(toJson(signal.evidence()));
        entity.setCreatedAt(createdAt);
        return entity;
    }

    private String toJson(Object value) {
        if (value == null) {
            return EMPTY_JSON;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Risk signal evidence is not valid JSON", exception);
        }
    }

    private String defaultText(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private RiskCaseSummaryResponse toSummary(RiskCaseEntity riskCase) {
        return new RiskCaseSummaryResponse(
                riskCase.getCaseId(),
                riskCase.getTransactionId(),
                riskCase.getAccountId(),
                riskCase.getStatus(),
                riskCase.getSeverity(),
                riskCase.getRingRisk(),
                riskCase.getConfidence(),
                riskCase.getRecommendation(),
                riskCase.getCreatedAt());
    }

    private BigDecimal maxRisk(RiskEvaluationResponse evaluation) {
        return java.util.stream.Stream.of(
                        evaluation.transactionRisk(),
                        evaluation.accountRisk(),
                        evaluation.behaviorRisk(),
                        evaluation.temporalRisk(),
                        evaluation.structuralRisk(),
                        evaluation.similarityRisk(),
                        evaluation.ringRisk())
                .filter(value -> value != null)
                .max(BigDecimal::compareTo)
                .orElse(BigDecimal.ZERO);
    }

    private RiskSeverity severityFor(BigDecimal score) {
        if (score.compareTo(new BigDecimal("0.90")) >= 0) {
            return RiskSeverity.CRITICAL;
        }
        if (score.compareTo(new BigDecimal("0.75")) >= 0) {
            return RiskSeverity.HIGH;
        }
        if (score.compareTo(new BigDecimal("0.50")) >= 0) {
            return RiskSeverity.MEDIUM;
        }
        return RiskSeverity.LOW;
    }
}
