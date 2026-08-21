package com.creditrisk.meta.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.meta.dto.BaseMonthResponse;
import com.creditrisk.meta.service.MetaService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * BO 화면에서 공통으로 사용하는 선택값 API를 제공한다.
 */
@RestController
@RequestMapping("/api/v1/meta")
public class MetaController {

    private final MetaService metaService;

    /**
     * 공통 선택값 서비스를 주입받는다.
     *
     * @param metaService 기준년월 서비스
     */
    public MetaController(MetaService metaService) {
        this.metaService = metaService;
    }

    /**
     * 기준년월 선택 목록과 기본 기준년월을 조회한다.
     *
     * @param request 요청 식별자 확인용 HTTP 요청
     * @return 기준년월 공통 응답
     */
    @GetMapping("/base-months")
    public ApiResponse<BaseMonthResponse> getBaseMonths(HttpServletRequest request) {
        // 데이터가 실제 존재하는 월만 반환해 빈 화면 이동을 방지한다.
        BaseMonthResponse response = metaService.getBaseMonths();
        return ApiResponse.success(response, RequestIds.from(request));
    }
}

