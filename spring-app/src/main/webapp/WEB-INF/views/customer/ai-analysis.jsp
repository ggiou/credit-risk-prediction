<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="ai-analysis" data-customer-id="${customerId}"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/><div class="page-actions"><button id="runPrediction" class="primary">AI 분석 실행</button></div><section class="metric-grid three"><article class="metric"><small>1개월 후</small><strong id="hazard1m">-</strong></article><article class="metric"><small>2개월 후</small><strong id="hazard2m">-</strong></article><article class="metric"><small>3개월 후</small><strong id="hazard3m">-</strong></article></section>
<section class="panel"><h2>주요 위험 요인</h2><div id="riskFactors" class="data-grid"></div></section><section class="panel"><h2>AI 설명</h2><p id="explanation" class="explanation">분석 결과가 없습니다.</p><div id="modelMeta" class="meta-row"></div></section><p id="pageError" class="error-message" hidden></p>
</main></div><script src="${pageContext.request.contextPath}/js/api.js"></script><script src="${pageContext.request.contextPath}/js/customer-detail.js"></script></body></html>

