package com.creditrisk.common.domain;

/** LLM 설명 생성 단계의 상태를 표현한다. */
public enum LlmStatus {
    NOT_REQUESTED,      // 요청 전
    COMPLETED,          // 성공
    FAILED              // 실패
}

