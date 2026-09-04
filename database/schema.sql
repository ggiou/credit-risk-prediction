CREATE DATABASE IF NOT EXISTS credit_risk
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE credit_risk;

CREATE TABLE IF NOT EXISTS customer (
    customer_id VARCHAR(32) NOT NULL COMMENT '비식별 고객 ID',
    display_name VARCHAR(100) NULL COMMENT '데모 화면 표시명',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE COMMENT '합성 데이터 여부',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id)
) COMMENT='고객 기준정보';

CREATE TABLE IF NOT EXISTS member_snapshot (
    customer_id VARCHAR(32) NOT NULL,
    base_ym CHAR(6) NOT NULL COMMENT '기준년월 YYYYMM',
    gender_code TINYINT NULL,
    age_band VARCHAR(20) NULL,
    life_stage VARCHAR(50) NULL,
    member_delinquency_flag TINYINT NULL,
    credit_membership_months INT NULL,
    valid_credit_card_count INT NULL,
    available_credit_card_count INT NULL,
    used_credit_card_count INT NULL,
    credit_usage_amount_r3m BIGINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id, base_ym),
    INDEX idx_member_snapshot_base_ym (base_ym, customer_id),
    CONSTRAINT fk_member_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
) COMMENT='회원 월별 스냅샷';

CREATE TABLE IF NOT EXISTS credit_snapshot (
    customer_id VARCHAR(32) NOT NULL,
    base_ym CHAR(6) NOT NULL,
    credit_limit_amount BIGINT NULL,
    cash_advance_limit_amount BIGINT NULL,
    credit_limit_amount_b1m BIGINT NULL,
    forced_limit_reduction_count_r12m INT NULL,
    forced_limit_reduction_amount_r12m BIGINT NULL,
    voluntary_limit_reduction_count_r12m INT NULL,
    limit_increase_count_r12m INT NULL,
    limit_review_request_count INT NULL,
    limit_request_rejection_count INT NULL,
    market_short_delinquency_flag_r3m TINYINT NULL,
    market_short_delinquency_flag_r6m TINYINT NULL,
    revolving_agreed_billing_rate DOUBLE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id, base_ym),
    INDEX idx_credit_snapshot_base_ym (base_ym, customer_id),
    CONSTRAINT fk_credit_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
) COMMENT='신용 및 한도 월별 스냅샷';

CREATE TABLE IF NOT EXISTS billing_snapshot (
    customer_id VARCHAR(32) NOT NULL,
    base_ym CHAR(6) NOT NULL,
    billed_amount_b0 BIGINT NULL,
    billed_amount_r3m BIGINT NULL,
    delinquency_count_r3m INT NULL,
    delinquency_count_r6m INT NULL,
    on_due_date_payment_month_count_r3m INT NULL,
    prepayment_count_r3m INT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id, base_ym),
    INDEX idx_billing_snapshot_base_ym (base_ym, customer_id),
    CONSTRAINT fk_billing_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
) COMMENT='청구 및 상환 월별 스냅샷';

CREATE TABLE IF NOT EXISTS balance_snapshot (
    customer_id VARCHAR(32) NOT NULL,
    base_ym CHAR(6) NOT NULL,
    balance_b0m BIGINT NULL,
    lump_sum_balance_b0m BIGINT NULL,
    installment_balance_b0m BIGINT NULL,
    cash_advance_balance_b0m BIGINT NULL,
    card_loan_balance_b0m BIGINT NULL,
    revolving_lump_sum_carryover_balance_b0m BIGINT NULL,
    cash_advance_balance_b1m BIGINT NULL,
    card_loan_balance_b1m BIGINT NULL,
    monthly_average_balance BIGINT NULL,
    delinquency_days_b1m INT NULL COMMENT '학습 정답 및 검증용, 모델 입력 제외',
    delinquency_balance_b0m BIGINT NULL COMMENT '학습 정답 및 검증용, 모델 입력 제외',
    last_delinquency_months_r15m INT NULL COMMENT '학습 정답 및 검증용, 모델 입력 제외',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (customer_id, base_ym),
    INDEX idx_balance_snapshot_base_ym (base_ym, customer_id),
    CONSTRAINT fk_balance_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
) COMMENT='카드 관련 잔액 월별 스냅샷';

CREATE TABLE IF NOT EXISTS feature_snapshot (
    feature_snapshot_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id VARCHAR(32) NOT NULL,
    base_ym CHAR(6) NOT NULL,
    feature_schema_version VARCHAR(32) NOT NULL DEFAULT 'v1',
    features JSON NOT NULL,
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (feature_snapshot_id),
    UNIQUE KEY uk_feature_customer_month_schema (customer_id, base_ym, feature_schema_version),
    INDEX idx_feature_base_ym (base_ym, customer_id),
    CONSTRAINT fk_feature_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
) COMMENT='모델 기본 피처 스냅샷';

CREATE TABLE IF NOT EXISTS prediction_result (
    prediction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    feature_snapshot_id BIGINT UNSIGNED NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    hazard_1m DOUBLE NOT NULL,
    hazard_2m DOUBLE NOT NULL,
    hazard_3m DOUBLE NOT NULL,
    cumulative_risk_3m DOUBLE NOT NULL,
    risk_grade VARCHAR(10) NOT NULL COMMENT 'NORMAL, INTEREST, CAUTION, WARNING',
    percentile DOUBLE NOT NULL COMMENT '10만 명 기준 고위험 상위 비율: 0에 가까울수록 고위험, 100에 가까울수록 저위험',
    reasons JSON NULL,
    explanation TEXT NULL,
    recommendation TEXT NULL COMMENT 'LLM reviewPoints 화면 호환 렌더링 문자열',
    llm_output JSON NULL COMMENT '검증 완료된 LLM 구조화 출력 원본',
    llm_status VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUESTED'
        COMMENT 'LLM 설명 생성 상태: NOT_REQUESTED=요청 전, COMPLETED=생성 완료, FAILED=생성 실패',
    prompt_version VARCHAR(64) NULL,
    predicted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (prediction_id),
    UNIQUE KEY uk_prediction_feature_model (feature_snapshot_id, model_version),
    INDEX idx_prediction_feature_model_time (feature_snapshot_id, model_version, predicted_at DESC),
    INDEX idx_prediction_grade_time (risk_grade, predicted_at DESC),
    CONSTRAINT fk_prediction_feature FOREIGN KEY (feature_snapshot_id)
        REFERENCES feature_snapshot (feature_snapshot_id),
    CONSTRAINT chk_hazard_1m CHECK (hazard_1m BETWEEN 0 AND 1),
    CONSTRAINT chk_hazard_2m CHECK (hazard_2m BETWEEN 0 AND 1),
    CONSTRAINT chk_hazard_3m CHECK (hazard_3m BETWEEN 0 AND 1),
    CONSTRAINT chk_cumulative_risk CHECK (cumulative_risk_3m BETWEEN 0 AND 1),
    CONSTRAINT chk_percentile CHECK (percentile BETWEEN 0 AND 100),
    CONSTRAINT chk_risk_grade CHECK (risk_grade IN ('NORMAL', 'INTEREST', 'CAUTION', 'WARNING')),
    CONSTRAINT chk_llm_status CHECK (llm_status IN ('NOT_REQUESTED', 'COMPLETED', 'FAILED'))
) COMMENT='모델 예측 및 LLM 설명 결과';
