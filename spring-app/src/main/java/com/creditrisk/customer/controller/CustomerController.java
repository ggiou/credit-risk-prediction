package com.creditrisk.customer.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.api.PageData;
import com.creditrisk.common.domain.AnalysisStatus;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.customer.dto.CustomerListItem;
import com.creditrisk.customer.dto.CustomerSummaryResponse;
import com.creditrisk.customer.dto.FinancialDataResponse;
import com.creditrisk.customer.service.CustomerDetailService;
import com.creditrisk.customer.service.CustomerService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.PathVariable;
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
    private final CustomerDetailService customerDetailService;

    /** 고객 검색 서비스를 주입받는다. */
    public CustomerController(CustomerService customerService, CustomerDetailService customerDetailService) {
        this.customerService = customerService;
        this.customerDetailService = customerDetailService;
    }

    /**
     * 선택 고객의 기준월 금융 요약과 최근 위험률 추이를 조회한다.
     */
    @GetMapping("/{customerId}/summary")
    public ApiResponse<CustomerSummaryResponse> getCustomerSummary(
            @PathVariable String customerId,
            @RequestParam(required = false) String baseYm,
            @RequestParam(defaultValue = "6") int trendMonths,
            HttpServletRequest request) {
        // 화면 차트의 과도한 조회를 막고 실제 데이터 기간 안에서 사용하도록 제한한다.
        QueryValidator.validateBaseYm(baseYm);
        if (trendMonths < 1 || trendMonths > 12) {
            throw new IllegalArgumentException("trendMonths는 1 이상 12 이하여야 합니다.");
        }
        CustomerSummaryResponse response = customerDetailService.getSummary(customerId, baseYm, trendMonths);
        return ApiResponse.success(response, RequestIds.from(request));
    }

    /**
     * 고객의 월별 카드 이용 및 카드 보유 현황을 조회한다.
     */
    @GetMapping("/{customerId}/financials/card-usage")
    public ApiResponse<FinancialDataResponse> getCardUsage(
            @PathVariable String customerId,
            @RequestParam(required = false) String baseYm,
            @RequestParam(defaultValue = "6") int months,
            HttpServletRequest request) {
        // 실제 데이터 기간을 고려해 한 번에 최대 12개월만 조회한다.
        QueryValidator.validateBaseYm(baseYm);
        validateMonths(months);
        FinancialDataResponse response = customerDetailService.getCardUsage(customerId, baseYm, months);
        return ApiResponse.success(response, RequestIds.from(request));
    }

    /**
     * 고객의 월별 청구금액과 연체·상환 행동을 조회한다.
     */
    @GetMapping("/{customerId}/financials/billing")
    public ApiResponse<FinancialDataResponse> getBilling(
            @PathVariable String customerId,
            @RequestParam(required = false) String baseYm,
            @RequestParam(defaultValue = "6") int months,
            HttpServletRequest request) {
        // 기준월과 조회 개수 검증을 공통 기준으로 적용한다.
        QueryValidator.validateBaseYm(baseYm);
        validateMonths(months);
        FinancialDataResponse response = customerDetailService.getBilling(customerId, baseYm, months);
        return ApiResponse.success(response, RequestIds.from(request));
    }

    /**
     * 고객의 월별 신용 및 카드 한도 정보를 조회한다.
     */
    @GetMapping("/{customerId}/financials/credit")
    public ApiResponse<FinancialDataResponse> getCredit(
            @PathVariable String customerId,
            @RequestParam(required = false) String baseYm,
            @RequestParam(defaultValue = "6") int months,
            HttpServletRequest request) {
        // 잘못된 월과 조회 범위를 Mapper 실행 전에 차단한다.
        QueryValidator.validateBaseYm(baseYm);
        validateMonths(months);
        FinancialDataResponse response = customerDetailService.getCredit(customerId, baseYm, months);
        return ApiResponse.success(response, RequestIds.from(request));
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

    /** 월별 금융 데이터 조회 개수를 검증한다. */
    private void validateMonths(int months) {
        // 화면 차트가 사용하는 범위만 허용해 불필요한 대량 조회를 막는다.
        if (months < 1 || months > 12) {
            throw new IllegalArgumentException("months는 1 이상 12 이하여야 합니다.");
        }
    }
}
