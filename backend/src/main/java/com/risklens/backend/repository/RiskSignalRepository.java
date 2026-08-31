package com.risklens.backend.repository;

import com.risklens.backend.entity.RiskSignalEntity;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RiskSignalRepository extends JpaRepository<RiskSignalEntity, UUID> {

    List<RiskSignalEntity> findByRiskCaseIdOrderByCreatedAtAsc(UUID riskCaseId);
}

