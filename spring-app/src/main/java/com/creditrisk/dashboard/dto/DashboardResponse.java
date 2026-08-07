package com.creditrisk.dashboard.dto;

import java.util.List;

/**
 * 대시보드의 요약 지표와 차트, 고위험 고객 목록을 전달한다.
 *
 * @param baseYm 기준년월
 * @param modelVersion 조회 모델 버전
 * @param summary 상단 요약 지표
 * @param riskDistribution 위험등급 분포
 * @param averageRiskByHorizon 예측기간별 평균 위험률
 * @param highRiskCustomers 고위험 고객 목록
 */
public record DashboardResponse(
        String baseYm,
        String modelVersion,
        Summary summary,
        List<RiskDistribution> riskDistribution,
        List<AverageRisk> averageRiskByHorizon,
        List<HighRiskCustomer> highRiskCustomers) {

    /** 대시보드 상단 요약 지표다. */
    public record Summary(
            long targetCustomerCount,
            long highRiskCustomerCount,
            long riskIncreasedCustomerCount,
            long predictionCompletedCount,
            double predictionCompletionRate) {
    }

    /** 위험등급별 고객 수와 비율이다. */
    public record RiskDistribution(
            String riskGrade,
            String riskGradeName,
            long count,
            double rate) {
    }

    /** 1개월, 2개월, 3개월 후 평균 위험률이다. */
    public record AverageRisk(int horizon, double riskRate) {
    }

    /** 상세 화면으로 이동할 수 있는 고위험 고객 요약이다. */
    public record HighRiskCustomer(
            String customerId,
            long predictionId,
            String riskGrade,
            String riskGradeName,
            double hazard1m,
            double hazard2m,
            double hazard3m,
            Double riskChange3m,
            String primaryRiskFactor) {
    }
}

