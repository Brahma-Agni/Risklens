package com.risklens.backend.controller;

import com.risklens.backend.dto.AnalystActionResponse;
import com.risklens.backend.service.AnalystDecisionService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/analyst-actions")
@RequiredArgsConstructor
@Validated
public class AnalystActionController {

    private final AnalystDecisionService analystDecisionService;

    @GetMapping
    public List<AnalystActionResponse> list(
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit) {
        return analystDecisionService.list(limit);
    }
}
