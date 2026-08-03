package com.creditrisk.common.domain;

/**
 * 모델이 저장하는 위험등급과 BO 화면 표시명을 연결한다.
 */
public enum RiskGrade {
    NORMAL("정상"),
    INTEREST("관심"),
    CAUTION("주의"),
    WARNING("경고");

    private final String displayName;

    RiskGrade(String displayName) {
        this.displayName = displayName;
    }

    /** 화면에 표시할 한글 등급명을 반환한다. */
    public String getDisplayName() {
        return displayName;
    }
}

