package com.creditrisk.customer.dto;

import java.util.List;

/**
 * 고객 목록의 검색, 위험률 범위, 페이지 조건이다.
 */
public record CustomerSearchCondition(
        String baseYm,
        String previousBaseYm,
        String customerId,
        List<String> customerIds,
        List<String> customerNames,
        String riskGrade,
        String analysisStatus,
        String analysisOrder,
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
