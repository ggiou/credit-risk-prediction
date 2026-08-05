package com.creditrisk.meta.service;

import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.meta.dto.BaseMonthResponse;
import com.creditrisk.meta.mapper.MetaMapper;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

/**
 * 화면 공통 검색 조건을 구성한다.
 */
@Service
public class MetaService {

    private final MetaMapper metaMapper;

    /**
     * 기준년월 조회 Mapper를 주입받는다.
     *
     * @param metaMapper 화면 공통 조회 Mapper
     */
    public MetaService(MetaMapper metaMapper) {
        this.metaMapper = metaMapper;
    }

    /**
     * 사용 가능한 기준년월과 기본 선택값을 반환한다.
     *
     * @return 기준년월 응답
     */
    public BaseMonthResponse getBaseMonths() {
        // 실제 적재된 피처만 화면에서 선택할 수 있도록 DB 결과를 사용한다.
        List<String> baseMonths = metaMapper.findBaseMonths();
        if (baseMonths.isEmpty()) {
            // 피처 적재가 실패한 경우 임의의 월을 반환하면 후속 조회가 모두 잘못되므로 명시적으로 실패시킨다.
            throw new BusinessException(
                    "BASE_MONTH_NOT_FOUND",
                    "조회 가능한 기준년월이 없습니다.",
                    HttpStatus.NOT_FOUND,
                    Map.of());
        }

        // SQL이 내림차순으로 조회하므로 첫 항목을 화면 기본값으로 사용한다.
        return new BaseMonthResponse(baseMonths.get(0), List.copyOf(baseMonths));
    }

    /**
     * 선택값이 없을 때 최신 기준년월을 보완한다.
     *
     * @param requestedBaseYm 화면에서 전달한 기준년월
     * @return 요청값 또는 최신 기준년월
     */
    public String resolveBaseYm(String requestedBaseYm) {
        // 빈 문자열도 선택하지 않은 값으로 간주한다.
        if (requestedBaseYm == null || requestedBaseYm.isBlank()) {
            return getBaseMonths().defaultBaseYm();
        }
        return requestedBaseYm;
    }
}

