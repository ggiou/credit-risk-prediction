package com.creditrisk.admin.config;

import com.creditrisk.admin.controller.BatchAdminSessionController;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

/** 로그인된 관리자 세션이 없는 다건 API 접근을 서버에서 차단한다. */
@Component
public class BatchAdminInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        var session = request.getSession(false);
        if (session != null && session.getAttribute(BatchAdminSessionController.SESSION_EMAIL) != null) return true;
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"success\":false,\"error\":{\"code\":\"ADMIN_LOGIN_REQUIRED\",\"message\":\"다건 AI 분석 관리자 로그인이 필요합니다.\"}}");
        return false;
    }
}
