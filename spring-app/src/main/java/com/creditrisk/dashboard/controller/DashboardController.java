package com.creditrisk.dashboard.controller;

import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.common.web.QueryValidator;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.dashboard.dto.DashboardResponse;
import com.creditrisk.dashboard.service.DashboardService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import org.springframework.http.HttpStatus;
import java.util.Map;

/**
 * BO 메인 대시보드 조회 API를 제공한다.
 */
@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardController {

    private final DashboardService dashboardService;

    /** 대시보드 서비스를 주입받는다. */
    public DashboardController(DashboardService dashboardService) {
        this.dashboardService = dashboardService;
    }

    /**
     * 기준월의 연체 위험 현황과 고위험 고객을 조회한다.
     *
     * @param baseYm 기준년월, 없으면 최신월
     * @param highRiskLimit 고위험 고객 표시 건수
     * @param request 요청 식별자 확인용 HTTP 요청
     * @return 대시보드 공통 응답
     */
    @GetMapping
    public ApiResponse<DashboardResponse> getDashboard(
            @RequestParam(required = false) String baseYm,
            @RequestParam(defaultValue = "5") int highRiskLimit,
            HttpServletRequest request) {
        // 서비스 호출 전에 값의 형식과 대량 조회 가능성을 차단한다.
        QueryValidator.validateBaseYm(baseYm);
        if (highRiskLimit < 1 || highRiskLimit > 20) {
            // 과도한 목록 조회는 잘못된 요청으로 분류하고 내부 오류로 처리하지 않는다.
            throw new BusinessException(
                    "INVALID_REQUEST",
                    "highRiskLimit은 1 이상 20 이하여야 합니다.",
                    HttpStatus.BAD_REQUEST,
                    Map.of("highRiskLimit", highRiskLimit));
        }

        DashboardResponse response = dashboardService.getDashboard(baseYm, highRiskLimit);
        return ApiResponse.success(response, RequestIds.from(request));
    }
}
