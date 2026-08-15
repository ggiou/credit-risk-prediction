package com.creditrisk.customer.dto;

import java.util.List;
import java.util.Map;

/**
 * 고객의 월별 금융 데이터와 선택 기준월 요약을 함께 전달한다.
 *
 * @param customerId 비식별 고객 ID
 * @param baseYm 선택 기준년월
 * @param summary 선택 기준년월의 지표
 * @param monthly 최근 월별 지표 목록
 */
public record FinancialDataResponse(
        String customerId,
        String baseYm,
        Map<String, Object> summary,
        List<Map<String, Object>> monthly) {
}

