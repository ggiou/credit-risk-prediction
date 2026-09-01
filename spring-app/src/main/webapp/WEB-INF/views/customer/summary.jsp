<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="customer-summary" data-customer-id="${customerId}"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/>
<section class="panel customer-status-summary" aria-labelledby="customerStatusTitle">
    <small>현재 고객 상태</small>
    <h2 id="customerStatusTitle"><span id="summaryCustomerName">고객</span>은 현재 <em id="riskGrade">미분석</em>이며,<br>기준집단 내 연체 위험 위치도 <em id="summaryRiskLevel">-</em>입니다.</h2>
    <p id="customerStatusDescription">최근 비교 가능한 이전 예측 결과는 없습니다.</p>
    <div class="customer-status-tags" aria-label="고객 핵심 상태">
        <span id="summaryMemberDelinquency">회원 연체 -</span>
        <span id="summaryRecentDelinquency">최근 3개월 연체 -</span>
        <span id="summaryUsedCards">이용 카드 -</span>
        <span id="summaryBaseMonth">기준월 -</span>
    </div>
</section>
<div class="summary-content-grid">
    <section class="panel key-customer-panel"><h2>핵심 고객 정보</h2><div id="customerInfo" class="data-grid summary-customer-grid"></div></section>
    <section class="panel"><h2>기준월별 3개월 후 위험률 추이</h2><div id="riskTrend" class="bar-list"></div></section>
</div>
<div class="summary-page-action"><a class="primary-link" href="${pageContext.request.contextPath}/customers/${customerId}/ai-analysis">AI 분석 상세 보기</a></div>
<p id="pageError" class="error-message" hidden></p>
</main></div><script src="${pageContext.request.contextPath}/js/api.js?v=20260830-3"></script><script src="${pageContext.request.contextPath}/js/customer-detail.js?v=20260901-1"></script></body></html>
