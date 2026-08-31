package com.risklens.backend.repository;

import com.risklens.backend.entity.TransactionEntity;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TransactionRepository extends JpaRepository<TransactionEntity, UUID> {

    Optional<TransactionEntity> findByTransactionId(String transactionId);

    boolean existsByTransactionId(String transactionId);

    List<TransactionEntity> findAllByOrderByOccurredAtDesc(Pageable pageable);

    List<TransactionEntity> findBySenderAccountIdOrderByOccurredAtDesc(
            String senderAccountId, Pageable pageable);
}

