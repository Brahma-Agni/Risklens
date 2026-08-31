package com.risklens.backend.dto;

import com.risklens.backend.domain.AnalystDecisionType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record AnalystDecisionRequest(
        @NotNull AnalystDecisionType decision,
        @NotBlank @Size(max = 128) String analyst,
        @Size(max = 2000) String comment
) {
}

