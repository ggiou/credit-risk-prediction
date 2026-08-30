<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<div class="customer-heading"><div><small><span id="customerDisplayHeading"></span><span id="customerDisplaySeparator" hidden> · </span>비식별 고객번호</small><h1>${customerId}</h1></div><div class="base-month-picker"><label>기준년<select id="baseYearSelect" data-base-year></select></label><label>기준월<select id="baseMonthSelect" data-base-month></select></label><select id="baseYmSelect" hidden aria-hidden="true" tabindex="-1"></select></div></div>
<nav class="tabs">
    <a class="${activeTab eq 'summary' ? 'active' : ''}" href="${pageContext.request.contextPath}/customers/${customerId}/summary">고객 요약</a>
    <a class="${activeTab eq 'financials' ? 'active' : ''}" href="${pageContext.request.contextPath}/customers/${customerId}/financials/card-usage">월별 금융 데이터</a>
    <a class="${activeTab eq 'ai-analysis' ? 'active' : ''}" href="${pageContext.request.contextPath}/customers/${customerId}/ai-analysis">AI 분석 결과</a>
    <a href="${pageContext.request.contextPath}/predictions?customerId=${customerId}">예측 이력</a>
</nav>
