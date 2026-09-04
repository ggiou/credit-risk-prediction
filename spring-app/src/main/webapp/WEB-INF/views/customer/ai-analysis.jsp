<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="ai-analysis" data-customer-id="${customerId}"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/>
<div id="predictionPageActions" class="page-actions" hidden><button id="runPrediction" class="primary">AI 분석 시작</button></div>
<section id="predictionEmptyState" class="panel prediction-empty-state" hidden>
    <div class="prediction-empty-header">
        <span class="prediction-empty-status"><i aria-hidden="true"></i>분석 대기</span>
        <strong id="predictionEmptyBaseYm">-</strong>
    </div>
    <div class="prediction-empty-content">
        <div class="prediction-empty-copy">
            <small>AI 연체 위험 분석</small>
            <h2>선택한 기준월의 분석을 시작해 주세요</h2>
            <p>현재 저장된 분석 결과가 없습니다. 고객의 금융 데이터를 분석해 관리에 필요한 위험 정보를 확인할 수 있습니다.</p>
        </div>
        <div class="prediction-empty-features" aria-label="분석 후 제공 정보">
            <div><span>01</span><p><strong>향후 위험률</strong><small>1·2·3개월 연체 위험률 비교</small></p></div>
            <div><span>02</span><p><strong>상대 위험 위치</strong><small>10만 명 비교군 기준 위험 상위 비율</small></p></div>
            <div><span>03</span><p><strong>주요 판단 지표</strong><small>모델 판단에 영향을 준 금융 지표</small></p></div>
        </div>
        <div class="prediction-empty-footer">
            <p>분석 결과는 관리자 판단을 지원하는 참고 정보로 제공됩니다.</p>
        </div>
    </div>
</section>
<div id="predictionResult" hidden>
<div class="analysis-overview" aria-label="AI 연체 위험 분석 결과">
    <section class="panel hazard-panel">
        <div class="panel-title"><h2>향후 월별 연체 위험률 비교</h2><span class="comparison-badge">확대 비교</span></div>
        <div class="hazard-bar-list">
            <div class="hazard-bar-row"><span>1개월 후</span><div class="hazard-track"><div class="hazard-fill" id="hazard1mBar"></div></div><strong id="hazard1m">-</strong></div>
            <div class="hazard-bar-row"><span>2개월 후</span><div class="hazard-track"><div class="hazard-fill" id="hazard2mBar"></div></div><strong id="hazard2m">-</strong></div>
            <div class="hazard-bar-row"><span>3개월 후</span><div class="hazard-track"><div class="hazard-fill" id="hazard3mBar"></div></div><strong id="hazard3m">-</strong></div>
        </div>
        <div class="hazard-chart-scale" aria-hidden="true"><span>0%</span><span>세 기간 내 상대 비교</span><strong id="hazardScaleMaximum">-</strong></div>
        <p class="hazard-scale-note">실제 0~100% 막대가 아니라, 매우 작은 세 위험률의 차이를 확인하기 위한 확대 표시입니다.</p>
    </section>
    <section class="panel risk-position-panel percentile-metric" id="riskPercentileCard">
        <div class="risk-position-heading">
            <div>
                <div class="metric-label">
                    <small>연체 위험 수준</small>
                    <button type="button" class="info-button" id="riskPercentileInfo" aria-label="연체 위험 수준 설명" aria-expanded="false" aria-describedby="riskPercentileTooltip">i</button>
                </div>
                <strong id="riskPercentile">-</strong>
            </div>
            <span class="risk-level risk-level-neutral" id="riskPercentileLevel">-</span>
        </div>
        <div class="risk-position-scale" aria-hidden="true"><span id="riskPercentileMarker"></span></div>
        <div class="risk-position-labels" aria-hidden="true"><span>낮음</span><span>평균</span><span>높음</span></div>
        <p id="riskPercentileNote">10만 명 비교군에서 위험 상위 몇 %인지 표시</p>
        <div class="risk-grade-line"><small>위험등급</small><strong id="predictionRiskGrade">-</strong></div>
        <div class="info-tooltip" id="riskPercentileTooltip" role="tooltip">값이 작을수록 더 위험합니다. 실제 연체 확률이 아닙니다.</div>
    </section>
</div>
<section class="panel risk-factor-panel">
    <h2>모델 판단에 영향을 준 주요 지표</h2>
    <p class="section-description">현재값을 전월값으로 되돌려 관련 파생 피처를 다시 계산·재채점한 비교 근거입니다. 고객별 SHAP 기여도나 실제 연체 원인을 의미하지 않습니다.</p>
    <div id="riskFactors" class="risk-factor-list"></div>
</section>
<section class="panel ai-explanation-panel">
    <h2 class="ai-explanation-title">AI 설명 <small>(LightGBM 근거 기반)</small></h2>
    <p id="explanationIntro" class="section-description" hidden>이 설명은 LightGBM 모델이 학습한 패턴과 고객의 최근 데이터를 기반으로 생성된 근거입니다.</p>
    <div id="explanation" class="explanation explanation-empty">분석 결과가 없습니다.</div>
    <div id="reviewPoints" class="explanation-review" hidden></div>
    <div id="keyIndicators" hidden></div>
    <p id="explanationNote" class="explanation-note">공공기관 생성 합성데이터 기반 모델의 조기경보 분석이며, 실제 연체 원인을 확정하지 않습니다.</p>
    <div id="modelMeta" class="meta-row"></div>
</section>
</div><p id="pageError" class="error-message" hidden></p>
</main></div><div id="predictionLoading" class="loading-overlay" role="status" aria-live="polite" aria-label="AI 분석 실행 중" hidden><div class="loading-dialog"><span class="loading-spinner" aria-hidden="true"></span><strong>AI 분석을 실행 중입니다.</strong><p>위험률과 주요 지표를 계산하고 있습니다.<br>잠시만 기다려 주세요.</p></div></div><script src="${pageContext.request.contextPath}/js/api.js?v=20260830-3"></script><script src="${pageContext.request.contextPath}/js/customer-detail.js?v=20260905-8"></script></body></html>
