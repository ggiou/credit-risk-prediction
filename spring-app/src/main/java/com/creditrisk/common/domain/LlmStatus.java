package com.creditrisk.common.domain;

/** LLM 설명 생성 단계의 상태를 표현한다. */
public enum LlmStatus {
    NOT_REQUESTED,      // 요청 전
    COMPLETED,          // 성공
    FAILED,             // 실패
    SKIPPED_NO_EVIDENCE // 모델 반사실 근거가 없어 LLM을 호출하지 않음
}
