package com.creditrisk.prediction.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.meta.service.MetaService;
import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.dto.PredictionCreateRequest;
import com.creditrisk.prediction.dto.PredictionExecutionResponse;
import com.creditrisk.prediction.service.PredictionCommandService;
import com.creditrisk.prediction.service.PredictionQueryService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 고객 상세 화면에서 사용하는 현재 예측 조회와 신규 분석 API를 제공한다.
 */
@RestController
@RequestMapping("/api/v1/customers/{customerId}/predictions")
public class CustomerPredictionController {

    private final PredictionQueryService predictionQueryService;
    private final PredictionCommandService predictionCommandService;
    private final MetaService metaService;

    /** 현재 예측 조회 서비스와 기준년월 서비스를 주입받는다. */
    public CustomerPredictionController(
            PredictionQueryService predictionQueryService,
            PredictionCommandService predictionCommandService,
            MetaService metaService) {
        this.predictionQueryService = predictionQueryService;
        this.predictionCommandService = predictionCommandService;
        this.metaService = metaService;
    }

    /**
     * 고객과 기준월의 활성 모델 최신 예측 결과를 조회한다.
     */
    @GetMapping("/current")
    public ApiResponse<PredictionDetailResponse> getCurrentPrediction(
            @PathVariable String customerId,
            @RequestParam(required = false) String baseYm,
            HttpServletRequest request) {
        // 기준월이 없으면 피처 스냅샷의 최신월로 보완한다.
        QueryValidator.validateBaseYm(baseYm);
        String resolvedBaseYm = metaService.resolveBaseYm(baseYm);
        PredictionDetailResponse response = predictionQueryService.getCurrent(customerId, resolvedBaseYm);
        return ApiResponse.success(response, RequestIds.from(request));
    }

    /**
     * 고객의 기준월 피처로 신규 예측을 실행하거나 동일 입력 결과를 재사용한다.
     */
    @PostMapping
    public ResponseEntity<ApiResponse<PredictionExecutionResponse>> createPrediction(
            @PathVariable String customerId,
            @Valid @RequestBody PredictionCreateRequest createRequest,
            HttpServletRequest request) {
        String requestId = RequestIds.from(request);
        PredictionExecutionResponse response = predictionCommandService.execute(
                customerId,
                createRequest.baseYm(),
                createRequest.shouldGenerateExplanation(),
                requestId);
        // 신규 저장은 201, 입력 해시 재사용은 200으로 반환한다.
        HttpStatus status = response.reused() ? HttpStatus.OK : HttpStatus.CREATED;
        return ResponseEntity.status(status)
                .body(ApiResponse.success(response, requestId));
    }
}
