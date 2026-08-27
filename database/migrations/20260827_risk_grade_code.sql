-- prediction_result.risk_grade를 화면 표시명이 아닌 영문 코드로 정규화한다.
-- 기존 환경마다 CHECK 이름이 다를 수 있어 risk_grade를 검사하는 제약을 먼저 조회해 제거한다.
SET @risk_grade_check_name = (
    SELECT tc.CONSTRAINT_NAME
    FROM information_schema.TABLE_CONSTRAINTS tc
    JOIN information_schema.CHECK_CONSTRAINTS cc
      ON cc.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
     AND cc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
    WHERE tc.CONSTRAINT_SCHEMA = DATABASE()
      AND tc.TABLE_NAME = 'prediction_result'
      AND tc.CONSTRAINT_TYPE = 'CHECK'
      AND cc.CHECK_CLAUSE LIKE '%risk_grade%'
    LIMIT 1
);
SET @risk_grade_check_exists = @risk_grade_check_name IS NOT NULL;
SET @risk_grade_check_name = COALESCE(@risk_grade_check_name, 'prediction_result_chk_6');

SET @drop_risk_grade_check_sql = IF(
    @risk_grade_check_exists,
    CONCAT('ALTER TABLE prediction_result DROP CHECK `', @risk_grade_check_name, '`'),
    'SELECT 1'
);
PREPARE drop_risk_grade_check FROM @drop_risk_grade_check_sql;
EXECUTE drop_risk_grade_check;
DEALLOCATE PREPARE drop_risk_grade_check;

UPDATE prediction_result
SET risk_grade = CASE risk_grade
    WHEN '정상' THEN 'NORMAL'
    WHEN '관심' THEN 'INTEREST'
    WHEN '주의' THEN 'CAUTION'
    WHEN '경고' THEN 'WARNING'
    ELSE risk_grade
END;

SET @add_risk_grade_check_sql = CONCAT(
    'ALTER TABLE prediction_result ADD CONSTRAINT `',
    @risk_grade_check_name,
    '` CHECK (risk_grade IN (''NORMAL'', ''INTEREST'', ''CAUTION'', ''WARNING''))'
);
PREPARE add_risk_grade_check FROM @add_risk_grade_check_sql;
EXECUTE add_risk_grade_check;
DEALLOCATE PREPARE add_risk_grade_check;
