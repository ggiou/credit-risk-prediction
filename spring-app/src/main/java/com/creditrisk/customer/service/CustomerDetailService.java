package com.creditrisk.customer.service;

import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.customer.dto.CustomerSummaryResponse;
import com.creditrisk.customer.dto.FinancialDataResponse;
import com.creditrisk.customer.mapper.CustomerDetailMapper;
import com.creditrisk.meta.service.MetaService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Collections;
import java.util.Map;

/**
 * 고객 상세 요약과 월별 금융 데이터를 구성한다.
 */
@Service
public class CustomerDetailService {

    private final CustomerDetailMapper customerDetailMapper;
    private final MetaService metaService;
    private final String modelVersion;

    /** 고객 상세 조회 의존성을 주입받는다. */
    public CustomerDetailService(
            CustomerDetailMapper customerDetailMapper,
            MetaService metaService,
            @Value("${ai.model.version}") String modelVersion) {
        this.customerDetailMapper = customerDetailMapper;
        this.metaService = metaService;
        this.modelVersion = modelVersion;
    }

    /**
     * 고객 기본 정보와 기준월 금융 요약, 위험률 추이를 조회한다.
     */
    public CustomerSummaryResponse getSummary(String customerId, String requestedBaseYm, int trendMonths) {
        // 고객이 없는 경우 금융 데이터 누락과 구분되는 오류를 먼저 반환한다.
        validateCustomer(customerId);
        String baseYm = metaService.resolveBaseYm(requestedBaseYm);
        Map<String, Object> row = customerDetailMapper.findCustomerSummary(customerId, baseYm, modelVersion);
        if (row == null || row.isEmpty()) {
            // 고객은 존재하지만 기준월 스냅샷이 적재되지 않은 상태다.
            throw new BusinessException(
                    "FEATURE_SNAPSHOT_NOT_FOUND",
                    "해당 고객과 기준월의 피처 스냅샷을 찾을 수 없습니다.",
                    HttpStatus.NOT_FOUND,
                    Map.of("customerId", customerId, "baseYm", baseYm));
        }

        List<CustomerSummaryResponse.RiskTrend> trend = customerDetailMapper
                .findRiskTrend(customerId, baseYm, modelVersion, trendMonths)
                .stream()
                .map(item -> new CustomerSummaryResponse.RiskTrend(
                        stringValue(item.get("baseYm")),
                        doubleValue(item.get("hazard1m")),
                        doubleValue(item.get("hazard2m")),
                        doubleValue(item.get("hazard3m"))))
                .toList();

        return new CustomerSummaryResponse(
                new CustomerSummaryResponse.Customer(
                        customerId,
                        nullableString(row.get("displayName")),
                        booleanValue(row.get("synthetic"))),
                baseYm,
                new CustomerSummaryResponse.Prediction(
                        nullableLong(row.get("predictionId")),
                        stringValue(row.get("analysisStatus")),
                        nullableString(row.get("riskGrade")),
                        nullableString(row.get("riskGradeName")),
                        nullableDouble(row.get("hazard1m")),
                        nullableDouble(row.get("hazard2m")),
                        nullableDouble(row.get("hazard3m")),
                        nullableDouble(row.get("percentile")),
                        instantValue(row.get("predictedAt"))),
                new CustomerSummaryResponse.CardUsageSummary(
                        nullableLong(row.get("creditUsageAmountR3m")),
                        nullableInteger(row.get("validCreditCardCount")),
                        nullableInteger(row.get("availableCreditCardCount")),
                        nullableInteger(row.get("usedCreditCardCount"))),
                new CustomerSummaryResponse.BillingSummary(
                        nullableLong(row.get("billedAmountB0")),
                        nullableInteger(row.get("delinquencyCountR3m")),
                        nullableInteger(row.get("onDueDatePaymentMonthCountR3m")),
                        nullableInteger(row.get("prepaymentCountR3m"))),
                new CustomerSummaryResponse.CreditSummary(
                        nullableLong(row.get("creditLimitAmount")),
                        nullableLong(row.get("cashAdvanceLimitAmount")),
                        nullableDouble(row.get("revolvingAgreedBillingRate"))),
                new CustomerSummaryResponse.BalanceSummary(
                        nullableLong(row.get("balanceB0m")),
                        nullableLong(row.get("cashAdvanceBalanceB0m")),
                        nullableLong(row.get("cardLoanBalanceB0m")),
                        nullableLong(row.get("revolvingCarryoverBalanceB0m"))),
                trend);
    }

    /**
     * 고객의 최근 카드 이용금액과 보유·사용 카드 수를 월별로 조회한다.
     */
    public FinancialDataResponse getCardUsage(String customerId, String requestedBaseYm, int months) {
        // 현재 DB에서 제공 가능한 최근 3개월 이용금액과 카드 수만 사용한다.
        validateCustomer(customerId);
        String baseYm = metaService.resolveBaseYm(requestedBaseYm);
        List<Map<String, Object>> monthly = customerDetailMapper.findCardUsage(customerId, baseYm, months);
        return financialResponse(customerId, baseYm, monthly, "MEMBER_SNAPSHOT_NOT_FOUND");
    }

    /**
     * 고객의 청구금액, 연체 건수, 상환 행동을 월별로 조회한다.
     */
    public FinancialDataResponse getBilling(String customerId, String requestedBaseYm, int months) {
        // 고객 존재 확인 후 청구 스냅샷만 별도로 조회해 다른 원천 누락의 영향을 받지 않게 한다.
        validateCustomer(customerId);
        String baseYm = metaService.resolveBaseYm(requestedBaseYm);
        List<Map<String, Object>> monthly = customerDetailMapper.findBilling(customerId, baseYm, months);
        return financialResponse(customerId, baseYm, monthly, "BILLING_SNAPSHOT_NOT_FOUND");
    }

    /**
     * 월별 조회 목록의 마지막 행을 기준월 요약으로 구성한다.
     */
    private FinancialDataResponse financialResponse(
            String customerId,
            String baseYm,
            List<Map<String, Object>> monthly,
            String errorCode) {
        if (monthly.isEmpty()) {
            // 원천 스냅샷 적재 실패를 빈 숫자나 0으로 숨기지 않고 화면에 구분해 알린다.
            throw new BusinessException(
                    errorCode,
                    "해당 고객과 기준월의 금융 스냅샷을 찾을 수 없습니다.",
                    HttpStatus.NOT_FOUND,
                    Map.of("customerId", customerId, "baseYm", baseYm));
        }

        // Mapper가 월 오름차순으로 반환하므로 마지막 행이 선택 기준월과 가장 가까운 최신 데이터다.
        Map<String, Object> summary = new LinkedHashMap<>(monthly.get(monthly.size() - 1));
        summary.remove("baseYm");
        // 금융 원천의 null은 결측값 의미가 있으므로 Map.copyOf로 제거하거나 실패시키지 않고 보존한다.
        return new FinancialDataResponse(
                customerId,
                baseYm,
                Collections.unmodifiableMap(summary),
                List.copyOf(monthly));
    }

    /**
     * 고객 존재 여부를 확인하고 없으면 명세된 오류를 발생시킨다.
     */
    public void validateCustomer(String customerId) {
        // 이후 모든 상세 API가 같은 존재 확인 기준을 사용한다.
        if (!customerDetailMapper.existsCustomer(customerId)) {
            throw new BusinessException(
                    "CUSTOMER_NOT_FOUND",
                    "고객을 찾을 수 없습니다.",
                    HttpStatus.NOT_FOUND,
                    Map.of("customerId", customerId));
        }
    }

    /** 문자열 DB 값을 반환한다. */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    /** null을 보존하는 문자열 변환이다. */
    private String nullableString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    /** null을 보존하는 Long 변환이다. */
    private Long nullableLong(Object value) {
        return value instanceof Number number ? number.longValue() : null;
    }

    /** null을 보존하는 Integer 변환이다. */
    private Integer nullableInteger(Object value) {
        return value instanceof Number number ? number.intValue() : null;
    }

    /** null을 보존하는 Double 변환이다. */
    private Double nullableDouble(Object value) {
        return value instanceof Number number ? number.doubleValue() : null;
    }

    /** null 숫자는 0으로 처리하는 차트용 변환이다. */
    private double doubleValue(Object value) {
        return value instanceof Number number ? number.doubleValue() : 0.0;
    }

    /** MySQL Boolean 표현을 자바 boolean으로 변환한다. */
    private boolean booleanValue(Object value) {
        return value instanceof Boolean bool ? bool : value instanceof Number number && number.intValue() == 1;
    }

    /** JDBC Timestamp를 UTC 시각으로 변환한다. */
    private Instant instantValue(Object value) {
        return value instanceof Timestamp timestamp ? timestamp.toInstant() : null;
    }
}
