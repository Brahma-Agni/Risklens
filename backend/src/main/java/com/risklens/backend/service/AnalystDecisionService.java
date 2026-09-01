package com.risklens.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.dto.AnalystDecisionRequest;
import com.risklens.backend.dto.AnalystDecisionResponse;
import com.risklens.backend.dto.AnalystActionResponse;
import com.risklens.backend.dto.CaseMemoryRequest;
import com.risklens.backend.entity.AnalystDecisionEntity;
import com.risklens.backend.entity.RiskCaseEntity;
import com.risklens.backend.exception.ConflictException;
import com.risklens.backend.repository.AnalystDecisionRepository;
import com.risklens.backend.repository.RiskCaseRepository;
import com.risklens.backend.repository.RiskSignalRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.domain.PageRequest;
import org.springframework.context.ApplicationEventPublisher;

@Service
@RequiredArgsConstructor
public class AnalystDecisionService {

    private final RiskCaseService riskCaseService;
    private final RiskCaseRepository riskCaseRepository;
    private final AnalystDecisionRepository analystDecisionRepository;
    private final RiskSignalRepository riskSignalRepository;
    private final ObjectMapper objectMapper;
    private final ApplicationEventPublisher eventPublisher;

    @Transactional(readOnly = true)
    public List<AnalystActionResponse> list(int limit) {
        return analystDecisionRepository
                .findAllByOrderByCreatedAtDesc(PageRequest.of(0, limit))
                .stream()
                .map(action -> new AnalystActionResponse(
                        action.getId(),
                        action.getRiskCase().getCaseId(),
                        action.getRiskCase().getTransactionId(),
                        action.getRiskCase().getAccountId(),
                        action.getDecision(),
                        action.getAnalystId(),
                        action.getComment(),
                        action.getCreatedAt()))
                .toList();
    }

    @Transactional
    public AnalystDecisionResponse decide(String caseId, AnalystDecisionRequest request) {
        RiskCaseEntity riskCase = riskCaseService.findEntityForUpdate(caseId);
        if (riskCase.getStatus() == RiskCaseStatus.RESOLVED) {
            throw new ConflictException("Risk case is already resolved: " + caseId);
        }

        Instant now = Instant.now();
        AnalystDecisionEntity decision = new AnalystDecisionEntity();
        decision.setRiskCase(riskCase);
        decision.setDecision(request.decision());
        decision.setAnalystId(request.analyst());
        decision.setComment(request.comment());
        decision.setCreatedAt(now);
        AnalystDecisionEntity saved = analystDecisionRepository.save(decision);

        riskCase.setStatus(RiskCaseStatus.RESOLVED);
        riskCase.setResolvedAt(now);
        riskCase.setUpdatedAt(now);
        riskCaseRepository.save(riskCase);

        eventPublisher.publishEvent(new CaseMemoryEvent(toMemoryRequest(
                riskCase, saved.getDecision(), saved.getComment())));

        return new AnalystDecisionResponse(
                saved.getId(),
                saved.getDecision(),
                saved.getAnalystId(),
                saved.getComment(),
                saved.getCreatedAt());
    }

    private CaseMemoryRequest toMemoryRequest(
            RiskCaseEntity riskCase,
            com.risklens.backend.domain.AnalystDecisionType label,
            String analystComment) {
        Map<String, Object> features = new LinkedHashMap<>();
        features.put("severity", riskCase.getSeverity().name());
        features.put("transactionRisk", riskCase.getTransactionRisk());
        features.put("accountRisk", riskCase.getAccountRisk());
        features.put("behaviorRisk", riskCase.getBehaviorRisk());
        features.put("temporalRisk", riskCase.getTemporalRisk());
        features.put("structuralRisk", riskCase.getStructuralRisk());
        features.put("similarityRisk", riskCase.getSimilarityRisk());
        features.put("ringRisk", riskCase.getRingRisk());
        features.put("confidence", riskCase.getConfidence());

        List<Map<String, Object>> evidence = new ArrayList<>();
        riskSignalRepository.findByRiskCaseIdOrderByCreatedAtAsc(riskCase.getId())
                .forEach(signal -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("type", signal.getSignalType());
                    item.put("source", signal.getSourceEngine());
                    item.put("score", signal.getScore());
                    item.put("description", signal.getDescription());
                    item.put("evidence", parseEvidence(signal.getEvidence()));
                    evidence.add(item);
                });

        String summary = String.join(" ",
                "Analyst resolved " + riskCase.getCaseId() + " as " + label.name() + ".",
                riskCase.getAiSummary() == null ? "" : riskCase.getAiSummary(),
                analystComment == null || analystComment.isBlank()
                        ? ""
                        : "Analyst note: " + analystComment);
        return new CaseMemoryRequest(riskCase.getCaseId(), label, summary, features, evidence);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseEvidence(String evidence) {
        if (evidence == null || evidence.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(evidence, Map.class);
        } catch (JsonProcessingException exception) {
            return Map.of("raw", evidence);
        }
    }
}
