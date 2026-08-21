package com.creditrisk.meta.dto;

import java.util.List;

/**
 * 화면 검색 조건에 사용할 기준년월 목록이다.
 *
 * @param defaultBaseYm 기본 선택 기준년월
 * @param baseMonths 내림차순 기준년월 목록
 */
public record BaseMonthResponse(String defaultBaseYm, List<String> baseMonths) {
}

