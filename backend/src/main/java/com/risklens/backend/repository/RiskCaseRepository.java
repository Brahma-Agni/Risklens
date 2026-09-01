package com.risklens.backend.repository;

import com.risklens.backend.domain.RiskCaseStatus;
import com.risklens.backend.domain.RiskSeverity;
import com.risklens.backend.entity.RiskCaseEntity;
import java.math.BigDecimal;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import jakarta.persistence.LockModeType;

public interface RiskCaseRepository extends JpaRepository<RiskCaseEntity, UUID> {

    Optional<RiskCaseEntity> findByCaseId(String caseId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select riskCase from RiskCaseEntity riskCase where riskCase.caseId = :caseId")
    Optional<RiskCaseEntity> findByCaseIdForUpdate(@Param("caseId") String caseId);

    Optional<RiskCaseEntity> findByTransactionId(String transactionId);

    List<RiskCaseEntity> findAllByOrderByCreatedAtDesc(Pageable pageable);

    List<RiskCaseEntity> findByStatusOrderByCreatedAtDesc(
            RiskCaseStatus status, Pageable pageable);

    List<RiskCaseEntity> findBySeverityOrderByCreatedAtDesc(
            RiskSeverity severity, Pageable pageable);

    List<RiskCaseEntity> findByStatusAndSeverityOrderByCreatedAtDesc(
            RiskCaseStatus status, RiskSeverity severity, Pageable pageable);

    List<RiskCaseEntity> findByStatusInAndRingRiskGreaterThanEqualOrderByRingRiskDescCreatedAtDesc(
            Collection<RiskCaseStatus> statuses, BigDecimal minimumRingRisk, Pageable pageable);
}
