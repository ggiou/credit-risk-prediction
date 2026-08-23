package com.creditrisk.customer.dto;

import java.time.Instant;
import java.util.List;

/**
 * 고객 상세의 요약 탭에서 사용하는 고객, 예측, 금융 지표다.
 */
public record CustomerSummaryResponse(
        Customer customer,
        String baseYm,
        Prediction prediction,
        CardUsageSummary cardUsageSummary,
        BillingSummary billingSummary,
        CreditSummary creditSummary,
        BalanceSummary balanceSummary,
        List<RiskTrend> riskTrend) {

    /** 비식별 고객 기본 정보다. */
    public record Customer(
            String customerId,
            String displayName,
            boolean synthetic,
            String ageBand,
            String lifeStage,
            Integer creditMembershipMonths,
            Boolean memberDelinquencyFlag) {
    }

    /** 기준월의 현재 예측 결과다. */
    public record Prediction(
            Long predictionId,
            String analysisStatus,
            String riskGrade,
            String riskGradeName,
            Double hazard1m,
            Double hazard2m,
            Double hazard3m,
            Double percentile,
            Instant predictedAt) {
    }

    /** 최근 카드 이용과 보유 카드 요약이다. */
    public record CardUsageSummary(
            Long creditUsageAmountR3m,
            Integer validCreditCardCount,
            Integer availableCreditCardCount,
            Integer usedCreditCardCount) {
    }

    /** 청구와 상환 행동 요약이다. */
    public record BillingSummary(
            Long billedAmountB0,
            Integer delinquencyCountR3m,
            Integer onDueDatePaymentMonthCountR3m,
            Integer prepaymentCountR3m) {
    }

    /** 신용한도와 리볼빙 요약이다. */
    public record CreditSummary(
            Long creditLimitAmount,
            Long cashAdvanceLimitAmount,
            Double revolvingAgreedBillingRate) {
    }

    /** 카드 관련 잔액 요약이다. */
    public record BalanceSummary(
            Long balanceB0m,
            Long cashAdvanceBalanceB0m,
            Long cardLoanBalanceB0m,
            Long revolvingCarryoverBalanceB0m) {
    }

    /** 고객의 월별 예측 위험률 변화다. */
    public record RiskTrend(String baseYm, double hazard1m, double hazard2m, double hazard3m) {
    }
}
