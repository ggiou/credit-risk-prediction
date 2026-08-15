package com.creditrisk.customer.dto;

/**
 * 고객 목록의 검색, 위험률 범위, 페이지 조건이다.
 */
public record CustomerSearchCondition(
        String baseYm,
        String previousBaseYm,
        String customerId,
        String riskGradeName,
        String analysisStatus,
        int horizon,
        Double minRiskRate,
        Double maxRiskRate,
        int page,
        int size,
        String sortField,
        String sortDirection,
        String modelVersion) {

    /** 조회 시작 위치를 계산한다. */
    public int offset() {
        // MySQL LIMIT 절에서 사용할 0 기반 시작 위치다.
        return page * size;
    }
}

