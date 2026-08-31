package com.risklens.backend.controller;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import com.risklens.backend.dto.AnalystDecisionRequest;
import com.risklens.backend.dto.AnalystDecisionResponse;
import com.risklens.backend.dto.RiskCaseDetailResponse;
import com.risklens.backend.dto.RiskCaseSummaryResponse;
import com.risklens.backend.service.AnalystDecisionService;
import com.risklens.backend.service.RiskCaseService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/risk-cases")
@RequiredArgsConstructor
@Validated
public class RiskCaseController {

    private final RiskCaseService riskCaseService;
    private final AnalystDecisionService analystDecisionService;

    @GetMapping
    public List<RiskCaseSummaryResponse> list(
            @RequestParam(required = false) RiskCaseStatus status,
            @RequestParam(required = false) RiskSeverity severity,
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit) {
        return riskCaseService.list(status, severity, limit);
    }

    @GetMapping("/{caseId}")
    public RiskCaseDetailResponse get(@PathVariable String caseId) {
        return riskCaseService.get(caseId);
    }

    @PostMapping("/{caseId}/decision")
    @ResponseStatus(HttpStatus.CREATED)
    public AnalystDecisionResponse decide(
            @PathVariable String caseId,
            @Valid @RequestBody AnalystDecisionRequest request) {
        return analystDecisionService.decide(caseId, request);
    }
}
