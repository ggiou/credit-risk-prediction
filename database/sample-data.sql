USE credit_risk;

INSERT INTO customer (customer_id, display_name, is_synthetic)
VALUES
    ('SYN_123', NULL, TRUE),
    ('SYN_456', NULL, TRUE),
    ('SYN_789', NULL, TRUE)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

INSERT INTO member_snapshot (
    customer_id, base_ym, gender_code, age_band, life_stage, member_delinquency_flag,
    credit_membership_months, valid_credit_card_count, available_credit_card_count,
    used_credit_card_count, credit_usage_amount_r3m
)
VALUES
    ('SYN_123', '201811', 1, '30대', '가족형성기', 0, 41, 4, 4, 3, 2490000),
    ('SYN_123', '201812', 1, '30대', '가족형성기', 0, 42, 4, 4, 3, 2840000),
    ('SYN_456', '201812', 2, '40대', '가족성숙기', 0, 68, 3, 3, 2, 1620000),
    ('SYN_789', '201812', 1, '20대', '사회초년기', 0, 18, 2, 2, 2, 980000)
ON DUPLICATE KEY UPDATE credit_usage_amount_r3m = VALUES(credit_usage_amount_r3m);

INSERT INTO credit_snapshot (
    customer_id, base_ym, credit_limit_amount, cash_advance_limit_amount, credit_limit_amount_b1m,
    forced_limit_reduction_count_r12m, forced_limit_reduction_amount_r12m,
    voluntary_limit_reduction_count_r12m, limit_increase_count_r12m,
    limit_review_request_count, limit_request_rejection_count,
    market_short_delinquency_flag_r3m, market_short_delinquency_flag_r6m,
    revolving_agreed_billing_rate
)
VALUES
    ('SYN_123', '201811', 5200000, 1000000, 5200000, 0, 0, 0, 1, 1, 0, 0, 0, 0.15),
    ('SYN_123', '201812', 5000000, 1000000, 5200000, 1, 200000, 0, 1, 2, 1, 1, 1, 0.20),
    ('SYN_456', '201812', 6000000, 1000000, 6000000, 0, 0, 0, 0, 0, 0, 0, 0, 0.05),
    ('SYN_789', '201812', 2500000, 500000, 2500000, 0, 0, 0, 0, 1, 0, 0, 0, 0.10)
ON DUPLICATE KEY UPDATE credit_limit_amount = VALUES(credit_limit_amount);

INSERT INTO billing_snapshot (
    customer_id, base_ym, billed_amount_b0, billed_amount_r3m, delinquency_count_r3m,
    delinquency_count_r6m, on_due_date_payment_month_count_r3m, prepayment_count_r3m
)
VALUES
    ('SYN_123', '201811', 2180000, 6480000, 1, 1, 2, 0),
    ('SYN_123', '201812', 2510000, 7150000, 1, 2, 2, 0),
    ('SYN_456', '201812', 1210000, 3520000, 0, 0, 3, 1),
    ('SYN_789', '201812', 870000, 2520000, 0, 0, 3, 0)
ON DUPLICATE KEY UPDATE billed_amount_b0 = VALUES(billed_amount_b0);

INSERT INTO balance_snapshot (
    customer_id, base_ym, balance_b0m, lump_sum_balance_b0m, installment_balance_b0m,
    cash_advance_balance_b0m, card_loan_balance_b0m,
    revolving_lump_sum_carryover_balance_b0m, cash_advance_balance_b1m,
    card_loan_balance_b1m, monthly_average_balance
)
VALUES
    ('SYN_123', '201811', 5610000, 1710000, 2050000, 650000, 1200000, 510000, 570000, 1050000, 5320000),
    ('SYN_123', '201812', 6420000, 1860000, 2340000, 780000, 1440000, 620000, 650000, 1200000, 5880000),
    ('SYN_456', '201812', 1740000, 920000, 620000, 0, 200000, 0, 0, 200000, 1680000),
    ('SYN_789', '201812', 1420000, 680000, 390000, 150000, 200000, 80000, 120000, 180000, 1310000)
ON DUPLICATE KEY UPDATE balance_b0m = VALUES(balance_b0m);

INSERT INTO feature_snapshot (customer_id, base_ym, feature_schema_version, features)
VALUES
    ('SYN_123', '201811', 'v1', JSON_OBJECT(
        '카드이용한도금액', 5200000, '청구금액_B0', 2180000, '잔액_B0M', 5610000,
        '잔액_현금서비스_B0M', 650000, '잔액_카드론_B0M', 1200000,
        '잔액_리볼빙일시불이월_B0M', 510000, '이용가능카드수_신용', 4, '유효카드수_신용', 4
    )),
    ('SYN_123', '201812', 'v1', JSON_OBJECT(
        '카드이용한도금액', 5000000, '카드이용한도금액_B1M', 5200000,
        '청구금액_B0', 2510000, '잔액_B0M', 6420000,
        '잔액_현금서비스_B0M', 780000, '잔액_현금서비스_B1M', 650000,
        '잔액_카드론_B0M', 1440000, '잔액_카드론_B1M', 1200000,
        '잔액_리볼빙일시불이월_B0M', 620000, '이용가능카드수_신용', 4, '유효카드수_신용', 4
    )),
    ('SYN_456', '201812', 'v1', JSON_OBJECT(
        '카드이용한도금액', 6000000, '청구금액_B0', 1210000, '잔액_B0M', 1740000,
        '잔액_현금서비스_B0M', 0, '잔액_카드론_B0M', 200000,
        '잔액_리볼빙일시불이월_B0M', 0, '이용가능카드수_신용', 3, '유효카드수_신용', 3
    )),
    ('SYN_789', '201812', 'v1', JSON_OBJECT(
        '카드이용한도금액', 2500000, '청구금액_B0', 870000, '잔액_B0M', 1420000,
        '잔액_현금서비스_B0M', 150000, '잔액_카드론_B0M', 200000,
        '잔액_리볼빙일시불이월_B0M', 80000, '이용가능카드수_신용', 2, '유효카드수_신용', 2
    ))
ON DUPLICATE KEY UPDATE feature_snapshot_id = feature_snapshot_id;

INSERT INTO prediction_result (
    feature_snapshot_id, model_version,
    hazard_1m, hazard_2m, hazard_3m, cumulative_risk_3m, risk_grade, percentile,
    reasons, explanation, llm_status, prompt_version, predicted_at
)
SELECT feature_snapshot_id,
       'miribom-lgbm-v0.3',
       CASE customer_id WHEN 'SYN_123' THEN 0.481 WHEN 'SYN_789' THEN 0.214 ELSE 0.082 END,
       CASE customer_id WHEN 'SYN_123' THEN 0.624 WHEN 'SYN_789' THEN 0.296 ELSE 0.124 END,
       CASE customer_id WHEN 'SYN_123' THEN 0.781 WHEN 'SYN_789' THEN 0.387 ELSE 0.181 END,
       CASE customer_id WHEN 'SYN_123' THEN 0.846 WHEN 'SYN_789' THEN 0.531 ELSE 0.329 END,
       CASE customer_id WHEN 'SYN_123' THEN 'WARNING' WHEN 'SYN_789' THEN 'CAUTION' ELSE 'NORMAL' END,
       CASE customer_id WHEN 'SYN_123' THEN 96.3 WHEN 'SYN_789' THEN 78.2 ELSE 34.1 END,
       CASE customer_id
           WHEN 'SYN_123' THEN JSON_ARRAY(JSON_OBJECT(
               'featureKey', 'f_사용률', 'displayName', '카드 한도 사용률',
               'direction', 'INCREASE', 'previousValue', 1.0788, 'currentValue', 1.284,
               'changeValue', 0.2052, 'changeRate', 0.1902, 'unit', 'RATIO', 'contribution', 0.128
           ))
           ELSE JSON_ARRAY()
       END,
       CASE customer_id
           WHEN 'SYN_123' THEN '카드 한도 사용률과 현금서비스 잔액이 전월보다 증가했습니다. 제공된 지표 변화가 향후 연체 위험 증가 요인으로 반영됐습니다.'
           ELSE '현재 제공된 카드 이용 및 상환 지표에서 큰 위험 변화는 확인되지 않았습니다.'
       END,
       'COMPLETED', 'v1.0', CURRENT_TIMESTAMP
FROM feature_snapshot
WHERE base_ym = '201812'
ON DUPLICATE KEY UPDATE predicted_at = VALUES(predicted_at);
