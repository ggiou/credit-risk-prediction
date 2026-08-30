<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="ai-analysis" data-customer-id="${customerId}"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/>
<div class="page-actions"><button id="runPrediction" class="primary">AI 분석 실행</button></div>
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
        <p id="riskPercentileNote">전체 고객과 비교한 상대적 위험 위치</p>
        <div class="risk-grade-line"><small>위험등급</small><strong id="predictionRiskGrade">-</strong></div>
        <div class="info-tooltip" id="riskPercentileTooltip" role="tooltip">상대적 위험 위치를 표시할 수 없습니다. 실제 연체 확률이 아닙니다.</div>
    </section>
</div>
<section class="panel risk-factor-panel">
    <h2>모델 판단에 영향을 준 주요 지표</h2>
    <p class="section-description">3개월 후 예측에서 모델 점수에 영향을 크게 준 입력 지표입니다. 실제 연체 원인이나 인과관계를 의미하지 않습니다.</p>
    <div id="riskFactors" class="risk-factor-list"></div>
</section>
<section class="panel"><h2>AI 설명</h2><p id="explanation" class="explanation">분석 결과가 없습니다.</p><div id="modelMeta" class="meta-row"></div></section><p id="pageError" class="error-message" hidden></p>
</main></div><div id="predictionLoading" class="loading-overlay" role="status" aria-live="polite" aria-label="AI 분석 실행 중" hidden><div class="loading-dialog"><span class="loading-spinner" aria-hidden="true"></span><strong>AI 분석을 실행 중입니다.</strong><p>위험률과 주요 지표를 계산하고 있습니다.<br>잠시만 기다려 주세요.</p></div></div><script src="${pageContext.request.contextPath}/js/api.js?v=20260830-3"></script><script src="${pageContext.request.contextPath}/js/customer-detail.js?v=20260830-5"></script></body></html>
