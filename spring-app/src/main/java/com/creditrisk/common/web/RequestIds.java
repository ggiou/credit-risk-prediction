package com.creditrisk.common.web;

import com.creditrisk.common.api.RequestIdFilter;
import jakarta.servlet.http.HttpServletRequest;

/**
 * Controller에서 현재 요청 식별자를 일관되게 읽도록 돕는다.
 */
public final class RequestIds {

    /**
     * 정적 유틸리티 클래스의 외부 인스턴스 생성을 막는다.
     */
    private RequestIds() {
        // 인스턴스를 만들 필요가 없는 정적 유틸리티 클래스다.
    }

    /**
     * 필터가 요청 속성에 저장한 추적 식별자를 반환한다.
     *
     * @param request 현재 HTTP 요청
     * @return 요청 추적 식별자
     */
    public static String from(HttpServletRequest request) {
        // 필터가 항상 값을 만들지만 방어적으로 문자열 변환을 사용한다.
        return String.valueOf(request.getAttribute(RequestIdFilter.ATTRIBUTE_NAME));
    }
}
