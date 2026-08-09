package com.creditrisk.customer.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.api.PageData;
import com.creditrisk.common.domain.AnalysisStatus;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.customer.dto.CustomerListItem;
import com.creditrisk.customer.service.CustomerService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Set;

/**
 * BO 고객 목록 검색 API를 제공한다.
 */
@RestController
@RequestMapping("/api/v1/customers")
public class CustomerController {

    private static final Set<String> SORT_FIELDS = Set.of(
            "customerId", "hazard1m", "hazard2m", "hazard3m", "riskChange3m", "predictedAt");

    private final CustomerService customerService;

    /** 고객 검색 서비스를 주입받는다. */
    public CustomerController(CustomerService customerService) {
        this.customerService = customerService;
    }

    /**
     * 고객번호, 위험등급, 분석 상태, 위험률 범위로 고객을 검색한다.
     */
    @GetMapping
    public ApiResponse<PageData<CustomerListItem>> searchCustomers(
            @RequestParam(required = false) String baseYm,
            @RequestParam(required = false) String customerId,
            @RequestParam(required = false) RiskGrade riskGrade,
            @RequestParam(required = false) AnalysisStatus analysisStatus,
            @RequestParam(defaultValue = "3") int horizon,
            @RequestParam(required = false) Double minRiskRate,
            @RequestParam(required = false) Double maxRiskRate,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "hazard3m,desc") String sort,
            HttpServletRequest request) {
        // 잘못된 기간과 동적 정렬값은 Mapper를 호출하기 전에 차단한다.
        QueryValidator.validateBaseYm(baseYm);
        QueryValidator.validatePage(page, size);
        QueryValidator.validateSort(sort, SORT_FIELDS);
        validateRiskRange(horizon, minRiskRate, maxRiskRate);

        PageData<CustomerListItem> response = customerService.searchCustomers(
                baseYm,
                customerId,
                riskGrade,
                analysisStatus == null ? null : analysisStatus.name(),
                horizon,
                minRiskRate,
                maxRiskRate,
                page,
                size,
                sort);
        return ApiResponse.success(response, RequestIds.from(request));
    }

    /**
     * 위험률 검색 기준과 최소·최대 범위를 검증한다.
     */
    private void validateRiskRange(int horizon, Double minRiskRate, Double maxRiskRate) {
        // 모델은 1, 2, 3개월 후 위험률만 제공한다.
        if (horizon < 1 || horizon > 3) {
            throw new IllegalArgumentException("horizon은 1 이상 3 이하여야 합니다.");
        }
        if ((minRiskRate != null && (minRiskRate < 0 || minRiskRate > 1))
                || (maxRiskRate != null && (maxRiskRate < 0 || maxRiskRate > 1))
                || (minRiskRate != null && maxRiskRate != null && minRiskRate > maxRiskRate)) {
            throw new IllegalArgumentException("위험률 범위는 0 이상 1 이하이며 최솟값이 최댓값보다 클 수 없습니다.");
        }
    }
}

