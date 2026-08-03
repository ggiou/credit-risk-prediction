package com.creditrisk.common.api;

import java.util.List;

/**
 * 목록 API의 페이지 정보와 조회 결과를 함께 전달한다.
 *
 * @param items 현재 페이지 항목
 * @param page 0부터 시작하는 페이지 번호
 * @param size 페이지 크기
 * @param totalElements 전체 항목 수
 * @param totalPages 전체 페이지 수
 * @param hasNext 다음 페이지 존재 여부
 * @param <T> 목록 항목 자료형
 */
public record PageData<T>(List<T> items, int page, int size, long totalElements, int totalPages, boolean hasNext) {

    /**
     * 조회 목록과 전체 건수로 페이지 응답을 계산한다.
     *
     * @param items 현재 페이지 항목
     * @param page 현재 페이지 번호
     * @param size 페이지 크기
     * @param totalElements 전체 항목 수
     * @return 계산된 페이지 응답
     * @param <T> 목록 항목 자료형
     */
    public static <T> PageData<T> of(List<T> items, int page, int size, long totalElements) {
        // 전체 건수가 페이지 크기로 나누어떨어지지 않는 경우 마지막 페이지를 포함한다.
        int totalPages = size == 0 ? 0 : (int) Math.ceil((double) totalElements / size);
        return new PageData<>(items, page, size, totalElements, totalPages, page + 1 < totalPages);
    }
}

