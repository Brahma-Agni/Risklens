package com.risklens.backend.controller;

import com.risklens.backend.dto.TransactionDetailResponse;
import com.risklens.backend.service.TransactionService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/accounts")
@RequiredArgsConstructor
@Validated
public class AccountController {

    private final TransactionService transactionService;

    @GetMapping("/{accountId}/transactions")
    public List<TransactionDetailResponse> transactions(
            @PathVariable String accountId,
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) int limit) {
        return transactionService.forAccount(accountId, limit);
    }
}

