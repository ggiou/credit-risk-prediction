package com.creditrisk.admin.controller;

import com.creditrisk.admin.dto.AdminLoginRequest;
import com.creditrisk.admin.service.BatchAdminAccessService;
import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.common.web.RequestIds;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 별도 다건 분석 화면의 관리자 세션을 생성하고 종료한다. */
@RestController
@RequestMapping("/api/v1/admin/session")
public class BatchAdminSessionController {

    public static final String SESSION_EMAIL = "BATCH_ADMIN_EMAIL";
    private final BatchAdminAccessService accessService;

    public BatchAdminSessionController(BatchAdminAccessService accessService) {
        this.accessService = accessService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> status(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        String email = session == null ? null : (String) session.getAttribute(SESSION_EMAIL);
        return ApiResponse.success(Map.of(
                "authenticated", email != null,
                "configured", accessService.configured(),
                "email", email == null ? "" : email), RequestIds.from(request));
    }

    @PostMapping
    public ApiResponse<Map<String, Object>> login(
            @Valid @RequestBody AdminLoginRequest body,
            HttpServletRequest request) {
        if (!accessService.authenticate(body.email(), body.password())) {
            throw new BusinessException("ADMIN_LOGIN_FAILED", "이메일 또는 비밀번호가 올바르지 않습니다.",
                    HttpStatus.UNAUTHORIZED, Map.of());
        }
        HttpSession session = request.getSession(true);
        request.changeSessionId();
        session.setAttribute(SESSION_EMAIL, body.email());
        return ApiResponse.success(Map.of("authenticated", true, "email", body.email()), RequestIds.from(request));
    }

    @DeleteMapping
    public ApiResponse<Map<String, Object>> logout(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session != null) session.invalidate();
        return ApiResponse.success(Map.of("authenticated", false), RequestIds.from(request));
    }
}
