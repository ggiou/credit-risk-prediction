-- 모델 반사실 근거가 없어 OpenAI를 호출하지 않은 상태를 실패와 분리한다.
SET @llm_status_check_name = (
    SELECT tc.CONSTRAINT_NAME
    FROM information_schema.TABLE_CONSTRAINTS tc
    JOIN information_schema.CHECK_CONSTRAINTS cc
      ON cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
     AND cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
    WHERE tc.CONSTRAINT_SCHEMA = DATABASE()
      AND tc.TABLE_NAME = 'prediction_result'
      AND tc.CONSTRAINT_TYPE = 'CHECK'
      AND cc.CHECK_CLAUSE LIKE '%llm_status%'
    LIMIT 1
);
SET @llm_status_check_exists = @llm_status_check_name IS NOT NULL;
SET @llm_status_check_name = COALESCE(@llm_status_check_name, 'chk_llm_status');

SET @drop_llm_status_check_sql = IF(
    @llm_status_check_exists,
    CONCAT('ALTER TABLE prediction_result DROP CHECK `', @llm_status_check_name, '`'),
    'SELECT 1'
);
PREPARE drop_llm_status_check FROM @drop_llm_status_check_sql;
EXECUTE drop_llm_status_check;
DEALLOCATE PREPARE drop_llm_status_check;

ALTER TABLE prediction_result
    MODIFY COLUMN llm_status VARCHAR(20) NOT NULL DEFAULT 'NOT_REQUESTED'
        COMMENT 'LLM 설명 상태: NOT_REQUESTED=미요청, COMPLETED=완료, FAILED=실패, SKIPPED_NO_EVIDENCE=근거 없음';

SET @add_llm_status_check_sql = CONCAT(
    'ALTER TABLE prediction_result ADD CONSTRAINT `',
    @llm_status_check_name,
    '` CHECK (llm_status IN (''NOT_REQUESTED'', ''COMPLETED'', ''FAILED'', ''SKIPPED_NO_EVIDENCE''))'
);
PREPARE add_llm_status_check FROM @add_llm_status_check_sql;
EXECUTE add_llm_status_check;
DEALLOCATE PREPARE add_llm_status_check;
