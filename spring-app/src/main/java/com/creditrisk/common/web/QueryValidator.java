package com.creditrisk.common.web;

import com.creditrisk.common.exception.BusinessException;
import org.springframework.http.HttpStatus;

import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * 목록·상세 API에서 공통으로 사용하는 쿼리값을 검증한다.
 */
public final class QueryValidator {

    private static final Pattern BASE_YM_PATTERN = Pattern.compile("^(19|20)\\d{2}(0[1-9]|1[0-2])$");

    /**
     * 정적 검증 유틸리티 클래스의 외부 인스턴스 생성을 막는다.
     */
    private QueryValidator() {
        // 인스턴스를 만들 필요가 없는 정적 유틸리티 클래스다.
    }

    /**
     * 기준년월이 YYYYMM 형식인지 확인한다.
     *
     * @param baseYm 검증할 기준년월
     */
    public static void validateBaseYm(String baseYm) {
        // 선택값은 서비스에서 최신 월로 보완하므로 null은 허용한다.
        if (baseYm != null && !BASE_YM_PATTERN.matcher(baseYm).matches()) {
            throw invalid("baseYm", baseYm, "기준년월은 YYYYMM 형식이어야 합니다.");
        }
    }

    /**
     * 페이지 번호와 크기가 허용 범위인지 확인한다.
     *
     * @param page 페이지 번호
     * @param size 페이지 크기
     */
    public static void validatePage(int page, int size) {
        // 과도한 조회로 DB와 화면이 느려지지 않도록 페이지 크기를 100으로 제한한다.
        if (page < 0 || size < 1 || size > 100) {
            throw invalid("page", page, "page는 0 이상, size는 1 이상 100 이하여야 합니다.");
        }
    }

    /**
     * 동적 정렬값이 허용된 필드와 방향만 사용하는지 확인한다.
     *
     * @param sort 쉼표로 구분된 정렬값
     * @param allowedFields 허용 필드
     */
    public static void validateSort(String sort, Set<String> allowedFields) {
        // MyBatis의 동적 정렬절에 임의 SQL이 들어가지 않도록 반드시 화이트리스트로 검사한다.
        String[] values = sort.split(",", -1);
        if (values.length != 2 || !allowedFields.contains(values[0])
                || !(values[1].equalsIgnoreCase("asc") || values[1].equalsIgnoreCase("desc"))) {
            throw invalid("sort", sort, "허용되지 않은 정렬 조건입니다.");
        }
    }

    /**
     * 잘못된 요청값을 공통 업무 예외로 변환한다.
     */
    private static BusinessException invalid(String field, Object value, String message) {
        // 실패한 필드와 값만 포함해 화면에서 수정할 항목을 확인할 수 있게 한다.
        return new BusinessException("INVALID_REQUEST", message, HttpStatus.BAD_REQUEST,
                Map.of("field", field, "value", String.valueOf(value)));
    }
}
