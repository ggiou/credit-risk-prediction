package com.creditrisk.prediction.mapper;

import com.creditrisk.prediction.dto.PredictionHistoryCondition;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * 예측 결과의 이력, 상세, 입력 스냅샷을 조회하고 신규 결과를 저장한다.
 */
@Mapper
public interface PredictionMapper {

    /** 검색 조건에 맞는 예측 이력을 조회한다. */
    List<Map<String, Object>> findHistory(@Param("condition") PredictionHistoryCondition condition);

    /** 검색 조건에 맞는 예측 이력 전체 건수를 조회한다. */
    long countHistory(@Param("condition") PredictionHistoryCondition condition);

    /** 예측 ID의 상세 결과를 조회한다. */
    Map<String, Object> findById(@Param("predictionId") long predictionId);

    /** 고객과 기준월의 활성 모델 최신 예측을 조회한다. */
    Map<String, Object> findCurrent(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("modelVersion") String modelVersion);

    /** 예측 실행에 사용할 현재·이전 피처 스냅샷을 조회한다. */
    List<Map<String, Object>> findFeatureSnapshots(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("previousBaseYm") String previousBaseYm);

    /** 동일 피처 스냅샷과 모델 버전으로 저장된 예측 결과를 조회한다. */
    Map<String, Object> findByFeatureSnapshotAndModel(
            @Param("featureSnapshotId") long featureSnapshotId,
            @Param("modelVersion") String modelVersion);

    /** FastAPI 검증이 끝난 예측 결과를 저장한다. */
    int insertPrediction(Map<String, Object> values);
}
