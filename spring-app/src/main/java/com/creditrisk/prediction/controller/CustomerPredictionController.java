package com.creditrisk.prediction.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.meta.service.MetaService;
import com.creditrisk.prediction.dto.PredictionDetailResponse;
import com.creditrisk.prediction.service.PredictionQueryService;
import jakarta.servlet.http.HttpServletRequest;
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
    private final MetaService metaService;

    /** 현재 예측 조회 서비스와 기준년월 서비스를 주입받는다. */
    public CustomerPredictionController(
            PredictionQueryService predictionQueryService,
            MetaService metaService) {
        this.predictionQueryService = predictionQueryService;
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
}

