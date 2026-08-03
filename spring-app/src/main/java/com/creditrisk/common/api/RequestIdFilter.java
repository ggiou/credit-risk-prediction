package com.creditrisk.common.api;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Optional;
import java.util.UUID;

/**
 * 요청마다 추적 식별자를 보장하고 응답 헤더와 로그 문맥에 전달한다.
 */
@Component
public class RequestIdFilter extends OncePerRequestFilter {

    public static final String HEADER_NAME = "X-Request-Id";
    public static final String ATTRIBUTE_NAME = "requestId";

    /**
     * 요청 헤더의 식별자를 재사용하거나 새 UUID를 발급한다.
     *
     * @param request HTTP 요청
     * @param response HTTP 응답
     * @param filterChain 다음 필터 체인
     * @throws ServletException 필터 처리 실패 시 발생
     * @throws IOException 입출력 실패 시 발생
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        // 호출자가 전달하지 않았거나 공백인 경우에만 서버에서 UUID를 생성한다.
        String requestId = Optional.ofNullable(request.getHeader(HEADER_NAME))
                .filter(value -> !value.isBlank())
                .orElseGet(() -> UUID.randomUUID().toString());

        request.setAttribute(ATTRIBUTE_NAME, requestId);
        response.setHeader(HEADER_NAME, requestId);
        MDC.put(ATTRIBUTE_NAME, requestId);

        try {
            // 동일 요청의 Controller와 후속 필터가 같은 식별자를 사용하도록 체인을 진행한다.
            filterChain.doFilter(request, response);
        } finally {
            // 스레드 풀에서 다음 요청에 이전 식별자가 섞이지 않도록 반드시 제거한다.
            MDC.remove(ATTRIBUTE_NAME);
        }
    }
}

