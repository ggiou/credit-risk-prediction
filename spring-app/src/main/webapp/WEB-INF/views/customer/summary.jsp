<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="customer-summary" data-customer-id="${customerId}"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/><section class="panel"><h2>고객 정보</h2><div id="customerInfo" class="data-grid"></div></section>
<section class="metric-grid three"><article class="metric"><small>현재 위험등급</small><strong id="riskGrade">-</strong></article><article class="metric"><small>1개월 후</small><strong id="hazard1m">-</strong></article><article class="metric"><small>3개월 후</small><strong id="hazard3m">-</strong></article></section>
<section class="panel"><h2>주요 금융 지표</h2><div id="financialSummary" class="data-grid"></div></section><section class="panel"><h2>최근 위험도 변화</h2><div id="riskTrend" class="bar-list"></div></section><p id="pageError" class="error-message" hidden></p>
</main></div><script src="${pageContext.request.contextPath}/js/api.js"></script><script src="${pageContext.request.contextPath}/js/customer-detail.js"></script></body></html>
