package com.creditrisk.prediction.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/**
 * 고객 기준월 예측 실행 요청이다.
 *
 * @param baseYm 예측 기준년월
 * @param generateExplanation LLM 설명 생성 여부
 */
public record PredictionCreateRequest(
        @NotBlank
        @Pattern(regexp = "^(19|20)\\d{2}(0[1-9]|1[0-2])$", message = "YYYYMM 형식이어야 합니다.")
        String baseYm,
        Boolean generateExplanation) {

    /** LLM 설명 생성 여부의 기본값을 적용한다. */
    public boolean shouldGenerateExplanation() {
        // 값이 생략되면 명세 기본값인 true를 사용한다.
        return generateExplanation == null || generateExplanation;
    }
}

