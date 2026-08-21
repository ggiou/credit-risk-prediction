<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="../common/head.jsp"/></head>
<body data-page="customer-financial" data-customer-id="${customerId}" data-financial-type="${financialType}"><jsp:include page="../common/sidebar.jsp"/><div class="app-shell"><jsp:include page="../common/header.jsp"/><main>
<jsp:include page="../common/customer-tabs.jsp"/><nav class="subtabs"><a class="${financialType eq 'card-usage' ? 'active' : ''}" href="card-usage">카드 이용</a><a class="${financialType eq 'billing' ? 'active' : ''}" href="billing">청구</a><a class="${financialType eq 'credit' ? 'active' : ''}" href="credit">신용</a><a class="${financialType eq 'balance' ? 'active' : ''}" href="balance">잔액</a></nav>
<section class="panel"><h2>${financialName} 기준월 요약</h2><div id="financialSummary" class="data-grid"></div></section><section class="panel"><h2>월별 ${financialName} 데이터</h2><div class="table-wrap"><table><thead id="financialHead"></thead><tbody id="financialTable"></tbody></table></div></section><p id="pageError" class="error-message" hidden></p>
</main></div><script src="${pageContext.request.contextPath}/js/api.js"></script><script src="${pageContext.request.contextPath}/js/customer-detail.js"></script></body></html>

