package com.risklens.backend.service;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.dto.AnalystDecisionRequest;
import com.risklens.backend.dto.AnalystDecisionResponse;
import com.risklens.backend.dto.AnalystActionResponse;
import com.risklens.backend.entity.AnalystDecisionEntity;
import com.risklens.backend.entity.RiskCaseEntity;
import com.risklens.backend.exception.ConflictException;
import com.risklens.backend.repository.AnalystDecisionRepository;
import com.risklens.backend.repository.RiskCaseRepository;
import java.time.Instant;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.domain.PageRequest;

@Service
@RequiredArgsConstructor
public class AnalystDecisionService {

    private final RiskCaseService riskCaseService;
    private final RiskCaseRepository riskCaseRepository;
    private final AnalystDecisionRepository analystDecisionRepository;

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
        RiskCaseEntity riskCase = riskCaseService.findEntity(caseId);
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

        return new AnalystDecisionResponse(
                saved.getId(),
                saved.getDecision(),
                saved.getAnalystId(),
                saved.getComment(),
                saved.getCreatedAt());
    }
}
