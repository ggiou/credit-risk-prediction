package com.creditrisk.common.domain;

/** 예측 결과와 LLM 설명 생성 여부를 함께 표현한다. */
public enum AnalysisStatus {
    NOT_ANALYZED,
    COMPLETED,
    PARTIAL
}

