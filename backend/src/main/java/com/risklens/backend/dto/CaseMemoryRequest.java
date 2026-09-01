package com.risklens.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.risklens.backend.domain.AnalystDecisionType;
import java.util.List;
import java.util.Map;

public record CaseMemoryRequest(
        @JsonProperty("risk_case_id") String riskCaseId,
        @JsonProperty("final_label") AnalystDecisionType finalLabel,
        @JsonProperty("case_summary") String caseSummary,
        @JsonProperty("feature_snapshot") Map<String, Object> featureSnapshot,
        @JsonProperty("evidence_snapshot") List<Map<String, Object>> evidenceSnapshot) {
}
