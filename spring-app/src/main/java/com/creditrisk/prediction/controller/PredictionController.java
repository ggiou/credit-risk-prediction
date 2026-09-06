package com.creditrisk.prediction.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.api.PageData;
import com.creditrisk.common.domain.LlmStatus;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.common.web.BulkSearchValues;
import com.creditrisk.prediction.dto.PredictionHistoryItem;
import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.service.PredictionHistoryService;
import com.creditrisk.prediction.service.PredictionQueryService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.List;
import java.util.Set;

/**
 * 전체 및 고객별 예측 결과 조회 API를 제공한다.
 */
@RestController
@RequestMapping("/api/v1/predictions")
public class PredictionController {

    private final PredictionHistoryService predictionHistoryService;
    private final PredictionQueryService predictionQueryService;

    /** 예측 이력 서비스를 주입받는다. */
    public PredictionController(
            PredictionHistoryService predictionHistoryService,
            PredictionQueryService predictionQueryService) {
        this.predictionHistoryService = predictionHistoryService;
        this.predictionQueryService = predictionQueryService;
    }

    /**
     * 선택한 예측 이력의 저장 결과를 상세 조회한다.
     */
    @GetMapping("/{predictionId}")
    public ApiResponse<PredictionDetailResponse> getPrediction(
            @PathVariable long predictionId,
            HttpServletRequest request) {
        // 양수가 아닌 ID는 DB를 조회하지 않고 잘못된 요청으로 처리한다.
        if (predictionId < 1) {
            throw new IllegalArgumentException("predictionId는 1 이상이어야 합니다.");
        }
        PredictionDetailResponse response = predictionQueryService.getById(predictionId);
        return ApiResponse.success(response, RequestIds.from(request));
    }

    /**
     * 고객, 기준월, 위험등급, 모델, LLM 상태로 예측 이력을 검색한다.
     */
    @GetMapping
    public ApiResponse<PageData<PredictionHistoryItem>> searchHistory(
            @RequestParam(required = false) String customerId,
            @RequestParam(required = false) List<String> customerIds,
            @RequestParam(required = false) List<String> customerNames,
            @RequestParam(required = false) String baseYm,
            @RequestParam(required = false) RiskGrade riskGrade,
            @RequestParam(required = false) String modelVersion,
            @RequestParam(required = false) LlmStatus llmStatus,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant predictedFrom,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant predictedTo,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "predictedAt,desc") String sort,
            HttpServletRequest request) {
        // 예측 이력은 분석일시만 정렬하도록 제한한다.
        QueryValidator.validateBaseYm(baseYm);
        QueryValidator.validatePage(page, size);
        QueryValidator.validateSort(sort, Set.of("predictedAt"));
        if (predictedFrom != null && predictedTo != null && predictedFrom.isAfter(predictedTo)) {
            throw new IllegalArgumentException("predictedFrom은 predictedTo보다 늦을 수 없습니다.");
        }
        List<String> normalizedCustomerIds = BulkSearchValues.normalize(customerIds, "customerIds");
        List<String> normalizedCustomerNames = BulkSearchValues.normalize(customerNames, "customerNames");
        if (normalizedCustomerIds != null && normalizedCustomerNames != null) {
            throw new IllegalArgumentException("customerIds와 customerNames는 동시에 사용할 수 없습니다.");
        }
        boolean hasBulkSearch = normalizedCustomerIds != null || normalizedCustomerNames != null;

        PageData<PredictionHistoryItem> response = predictionHistoryService.search(
                hasBulkSearch ? null : customerId,
                normalizedCustomerIds,
                normalizedCustomerNames,
                baseYm,
                riskGrade,
                modelVersion,
                llmStatus,
                predictedFrom,
                predictedTo,
                page,
                size,
                sort);
        return ApiResponse.success(response, RequestIds.from(request));
    }

}
