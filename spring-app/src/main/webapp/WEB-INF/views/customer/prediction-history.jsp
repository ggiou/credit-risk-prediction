<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="customer-prediction-history" data-customer-id="${customerId}" data-customer-base-path="${pageContext.request.contextPath}/customers"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/>
<section class="panel customer-history-trend-panel" aria-labelledby="customerHistoryTrendTitle">
    <div class="panel-title"><div><h2 id="customerHistoryTrendTitle">기준월별 1·2·3개월 연체 위험률 추이</h2><p>가로축은 기준월이며, 각 월에 저장된 가장 최근 예측 결과를 비교합니다.</p></div><div class="customer-history-legend" aria-label="그래프 범례"><span class="horizon-one">1개월</span><span class="horizon-two">2개월</span><span class="horizon-three">3개월</span></div></div>
    <div id="customerHistoryChart" class="customer-history-chart" aria-live="polite"></div>
</section>
<section class="panel customer-history-table-panel" aria-labelledby="customerHistoryTableTitle">
    <div class="panel-title"><h2 id="customerHistoryTableTitle">전체 실행 이력</h2><span id="customerHistoryCount">0건</span></div>
    <div class="table-wrap"><table><thead><tr><th>분석일시</th><th>기준월</th><th>1개월</th><th>2개월</th><th>3개월</th><th>등급</th><th>모델</th><th>LLM</th><th>상세</th></tr></thead><tbody id="customerHistoryTable"></tbody></table></div>
</section>
<p id="pageError" class="error-message" hidden></p>
</main></div><script src="${pageContext.request.contextPath}/js/api.js?v=20260906-1"></script><script src="${pageContext.request.contextPath}/js/customer-prediction-history.js?v=20260906-1"></script></body></html>
