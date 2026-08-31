package com.risklens.backend.repository;

import com.risklens.backend.entity.AnalystDecisionEntity;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AnalystDecisionRepository extends JpaRepository<AnalystDecisionEntity, UUID> {

    List<AnalystDecisionEntity> findByRiskCaseIdOrderByCreatedAtDesc(UUID riskCaseId);

    List<AnalystDecisionEntity> findAllByOrderByCreatedAtDesc(Pageable pageable);
}
