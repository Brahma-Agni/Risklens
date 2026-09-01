package com.risklens.backend.entity;

import com.risklens.backend.domain.TransactionStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "transactions")
@Getter
@Setter
@NoArgsConstructor
public class TransactionEntity {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "transaction_id", nullable = false, unique = true, length = 64)
    private String transactionId;

    @Column(name = "sender_account_id", nullable = false, length = 64)
    private String senderAccountId;

    @Column(name = "receiver_id", nullable = false, length = 64)
    private String receiverId;

    @Column(nullable = false, precision = 18, scale = 2)
    private BigDecimal amount;

    @Column(nullable = false, length = 3)
    private String currency;

    @Column(name = "device_id", length = 128)
    private String deviceId;

    @JdbcTypeCode(SqlTypes.INET)
    @Column(name = "ip_address", columnDefinition = "inet")
    private String ipAddress;

    @Column(name = "payment_method", nullable = false, length = 32)
    private String paymentMethod;

    @Column(name = "ip_id", length = 128)
    private String ipId;

    @Column(name = "payment_instrument_id", length = 128)
    private String paymentInstrumentId;

    @Column(name = "location_city", length = 128)
    private String locationCity;

    @Column(name = "location_state", length = 128)
    private String locationState;

    @Column(name = "location_country", length = 2)
    private String locationCountry;

    @Column(name = "authorization_status", length = 32)
    private String authorizationStatus;

    @Column(name = "authentication_status", length = 32)
    private String authenticationStatus;

    @Column(name = "processing_status", length = 32)
    private String processingStatus;

    @Column(name = "failure_reason", length = 64)
    private String failureReason;

    @Column(name = "merchant_category", length = 64)
    private String merchantCategory;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private String context;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "received_at", nullable = false)
    private Instant receivedAt;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.NAMED_ENUM)
    @Column(nullable = false, columnDefinition = "transaction_status")
    private TransactionStatus status;

    @Column(name = "risk_score", precision = 5, scale = 4)
    private BigDecimal riskScore;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "raw_payload", nullable = false, columnDefinition = "jsonb")
    private String rawPayload;
}
