package com.creditrisk.dashboard.service;

import com.creditrisk.dashboard.dto.DashboardResponse;
import com.creditrisk.dashboard.mapper.DashboardMapper;
import com.creditrisk.meta.service.MetaService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 기준월의 예측 현황을 대시보드 응답으로 구성한다.
 */
@Service
public class DashboardService {

    private static final DateTimeFormatter BASE_YM_FORMAT = DateTimeFormatter.ofPattern("yyyyMM");

    private final DashboardMapper dashboardMapper;
    private final MetaService metaService;
    private final String modelVersion;

    /**
     * 대시보드 조회에 필요한 Mapper와 활성 모델 정보를 주입받는다.
     */
    public DashboardService(
            DashboardMapper dashboardMapper,
            MetaService metaService,
            @Value("${ai.model.version}") String modelVersion) {
        this.dashboardMapper = dashboardMapper;
        this.metaService = metaService;
        this.modelVersion = modelVersion;
    }

    /**
     * 대시보드 요약 지표와 차트 데이터를 조회한다.
     *
     * @param requestedBaseYm 화면에서 선택한 기준년월
     * @param highRiskLimit 고위험 고객 표시 건수
     * @return 대시보드 응답
     */
    public DashboardResponse getDashboard(String requestedBaseYm, int highRiskLimit) {
        // 기준월이 없으면 실제 피처가 적재된 최신월을 사용한다.
        String baseYm = metaService.resolveBaseYm(requestedBaseYm);
        String previousBaseYm = YearMonth.parse(baseYm, BASE_YM_FORMAT).minusMonths(1).format(BASE_YM_FORMAT);

        long targetCount = dashboardMapper.countTargetCustomers(baseYm);
        Map<String, Object> summaryRow = dashboardMapper.findPredictionSummary(
                baseYm, previousBaseYm, modelVersion);

        long completedCount = longValue(summaryRow.get("predictionCompletedCount"));
        double completionRate = targetCount == 0 ? 0.0 : (double) completedCount / targetCount;
        DashboardResponse.Summary summary = new DashboardResponse.Summary(
                targetCount,
                longValue(summaryRow.get("highRiskCustomerCount")),
                longValue(summaryRow.get("riskIncreasedCustomerCount")),
                completedCount,
                completionRate);

        // 등급이 하나도 없는 경우에도 화면 차트가 안정적으로 렌더링되도록 빈 목록을 허용한다.
        List<DashboardResponse.RiskDistribution> distribution = dashboardMapper
                .findRiskDistribution(baseYm, modelVersion)
                .stream()
                .map(row -> new DashboardResponse.RiskDistribution(
                        stringValue(row.get("riskGrade")),
                        stringValue(row.get("riskGradeName")),
                        longValue(row.get("count")),
                        completedCount == 0 ? 0.0 : (double) longValue(row.get("count")) / completedCount))
                .toList();

        Map<String, Object> averageRow = dashboardMapper.findAverageRisk(baseYm, modelVersion);
        List<DashboardResponse.AverageRisk> averages = List.of(
                new DashboardResponse.AverageRisk(1, doubleValue(averageRow.get("hazard1m"))),
                new DashboardResponse.AverageRisk(2, doubleValue(averageRow.get("hazard2m"))),
                new DashboardResponse.AverageRisk(3, doubleValue(averageRow.get("hazard3m"))));

        List<DashboardResponse.HighRiskCustomer> highRiskCustomers = new ArrayList<>();
        for (Map<String, Object> row : dashboardMapper.findHighRiskCustomers(
                baseYm, previousBaseYm, modelVersion, highRiskLimit)) {
            // reasons JSON의 첫 표시명은 SQL에서 추출하며 없는 경우 기본 문구를 사용한다.
            highRiskCustomers.add(new DashboardResponse.HighRiskCustomer(
                    stringValue(row.get("customerId")),
                    longValue(row.get("predictionId")),
                    stringValue(row.get("riskGrade")),
                    stringValue(row.get("riskGradeName")),
                    doubleValue(row.get("hazard1m")),
                    doubleValue(row.get("hazard2m")),
                    doubleValue(row.get("hazard3m")),
                    nullableDouble(row.get("riskChange3m")),
                    stringValue(row.get("primaryRiskFactor"))));
        }

        return new DashboardResponse(baseYm, modelVersion, summary, distribution, averages, highRiskCustomers);
    }

    /** 숫자형 DB 값을 long으로 안전하게 변환한다. */
    private long longValue(Object value) {
        return value instanceof Number number ? number.longValue() : 0L;
    }

    /** 숫자형 DB 값을 double로 안전하게 변환한다. */
    private double doubleValue(Object value) {
        return value instanceof Number number ? number.doubleValue() : 0.0;
    }

    /** null을 보존하면서 숫자형 DB 값을 double로 변환한다. */
    private Double nullableDouble(Object value) {
        return value instanceof Number number ? number.doubleValue() : null;
    }

    /** null DB 문자열을 빈 문자열로 변환한다. */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }
}

