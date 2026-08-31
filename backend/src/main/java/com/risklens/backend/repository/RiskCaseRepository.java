package com.risklens.backend.repository;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import com.risklens.backend.entity.RiskCaseEntity;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RiskCaseRepository extends JpaRepository<RiskCaseEntity, UUID> {

    Optional<RiskCaseEntity> findByCaseId(String caseId);

    Optional<RiskCaseEntity> findByTransactionId(String transactionId);

    List<RiskCaseEntity> findAllByOrderByCreatedAtDesc(Pageable pageable);

    List<RiskCaseEntity> findByStatusOrderByCreatedAtDesc(
            RiskCaseStatus status, Pageable pageable);

    List<RiskCaseEntity> findBySeverityOrderByCreatedAtDesc(
            RiskSeverity severity, Pageable pageable);

    List<RiskCaseEntity> findByStatusAndSeverityOrderByCreatedAtDesc(
            RiskCaseStatus status, RiskSeverity severity, Pageable pageable);
}

