package com.creditrisk.prediction.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.util.List;

/** 관리자가 선택한 고객의 다건 분석 요청이다. */
public record PredictionBatchCreateRequest(
        @NotBlank @Pattern(regexp = "^(19|20)\\d{2}(0[1-9]|1[0-2])$") String baseYm,
        @NotEmpty @Size(max = 50) List<@NotBlank String> customerIds,
        Boolean generateExplanation) {

    public boolean shouldGenerateExplanation() {
        return generateExplanation == null || generateExplanation;
    }
}
