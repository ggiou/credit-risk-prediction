package com.creditrisk.customer.dto;

/**
 * 고객 목록의 검색, 위험률 범위, 페이지 조건이다.
 */
public record CustomerSearchCondition(
        String baseYm,
        String previousBaseYm,
        String customerId,
        String riskGrade,
        String analysisStatus,
        int horizon,
        Double minRiskRate,
        Double maxRiskRate,
        int page,
        int size,
        int offset,
        String sortField,
        String sortDirection,
        String modelVersion,
        String promptVersion) {
}
