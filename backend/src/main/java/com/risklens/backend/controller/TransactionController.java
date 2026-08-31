package com.risklens.backend.controller;

import com.risklens.backend.dto.TransactionDetailResponse;
import com.risklens.backend.dto.TransactionRequest;
import com.risklens.backend.dto.TransactionResponse;
import com.risklens.backend.service.TransactionService;
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
@RequestMapping("/api/v1/transactions")
@RequiredArgsConstructor
@Validated
public class TransactionController {

    private final TransactionService transactionService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public TransactionResponse create(@Valid @RequestBody TransactionRequest request) {
        return transactionService.process(request);
    }

    @GetMapping("/{transactionId}")
    public TransactionDetailResponse get(@PathVariable String transactionId) {
        return transactionService.get(transactionId);
    }

    @GetMapping
    public List<TransactionDetailResponse> recent(
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit) {
        return transactionService.recent(limit);
    }
}

