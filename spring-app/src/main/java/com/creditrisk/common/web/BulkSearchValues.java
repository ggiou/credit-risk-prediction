package com.creditrisk.common.web;

import java.util.LinkedHashSet;
import java.util.List;

/** 고객번호·고객명 다량 검색값을 API 공통 규칙으로 정리한다. */
public final class BulkSearchValues {

    private static final int MAX_VALUES = 50;

    private BulkSearchValues() {
    }

    /** 공백과 중복을 제거하고 입력 순서를 유지하며 최대 조회 개수를 검증한다. */
    public static List<String> normalize(List<String> values, String parameterName) {
        if (values == null) {
            return null;
        }
        List<String> normalized = new LinkedHashSet<>(values.stream()
                .filter(value -> value != null && !value.isBlank())
                .map(String::trim)
                .toList()).stream().toList();
        if (normalized.isEmpty()) {
            return null;
        }
        if (normalized.size() > MAX_VALUES) {
            throw new IllegalArgumentException(parameterName + "는 최대 " + MAX_VALUES + "개까지 조회할 수 있습니다.");
        }
        return normalized;
    }
}
