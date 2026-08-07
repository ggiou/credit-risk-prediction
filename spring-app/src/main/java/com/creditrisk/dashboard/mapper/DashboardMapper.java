package com.creditrisk.dashboard.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * 대시보드 지표와 고위험 고객을 조회한다.
 */
@Mapper
public interface DashboardMapper {

    /** 기준년월의 분석 대상 고객 수를 조회한다. */
    long countTargetCustomers(@Param("baseYm") String baseYm);

    /** 기준년월과 모델 버전에 해당하는 예측 집계를 조회한다. */
    Map<String, Object> findPredictionSummary(
            @Param("baseYm") String baseYm,
            @Param("previousBaseYm") String previousBaseYm,
            @Param("modelVersion") String modelVersion);

    /** 위험등급별 고객 수를 조회한다. */
    List<Map<String, Object>> findRiskDistribution(
            @Param("baseYm") String baseYm,
            @Param("modelVersion") String modelVersion);

    /** 1개월, 2개월, 3개월 후 평균 위험률을 조회한다. */
    Map<String, Object> findAverageRisk(
            @Param("baseYm") String baseYm,
            @Param("modelVersion") String modelVersion);

    /** 위험률이 높은 고객을 제한 건수만큼 조회한다. */
    List<Map<String, Object>> findHighRiskCustomers(
            @Param("baseYm") String baseYm,
            @Param("previousBaseYm") String previousBaseYm,
            @Param("modelVersion") String modelVersion,
            @Param("limit") int limit);
}

