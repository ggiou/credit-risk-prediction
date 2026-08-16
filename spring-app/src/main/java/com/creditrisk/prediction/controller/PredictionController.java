package com.creditrisk.prediction.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.api.PageData;
import com.creditrisk.common.domain.LlmStatus;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.prediction.dto.PredictionHistoryItem;
import com.creditrisk.prediction.service.PredictionHistoryService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Set;

/**
 * 전체 및 고객별 예측 결과 조회 API를 제공한다.
 */
@RestController
@RequestMapping("/api/v1/predictions")
public class PredictionController {

    private final PredictionHistoryService predictionHistoryService;

    /** 예측 이력 서비스를 주입받는다. */
    public PredictionController(PredictionHistoryService predictionHistoryService) {
        this.predictionHistoryService = predictionHistoryService;
    }

    /**
     * 고객, 기준월, 위험등급, 모델, LLM 상태로 예측 이력을 검색한다.
     */
    @GetMapping
    public ApiResponse<PageData<PredictionHistoryItem>> searchHistory(
            @RequestParam(required = false) String customerId,
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

        PageData<PredictionHistoryItem> response = predictionHistoryService.search(
                customerId,
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

