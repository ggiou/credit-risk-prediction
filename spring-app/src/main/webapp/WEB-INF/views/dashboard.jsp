<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html><html lang="ko"><head><jsp:include page="common/head.jsp"/></head>
<body data-page="dashboard"><jsp:include page="common/sidebar.jsp"/><div class="app-shell"><jsp:include page="common/header.jsp"/><main>
<div class="page-title"><div><h1>대시보드</h1><p>기준월별 고객 연체 위험 현황을 확인합니다.</p></div><label>기준월 <select id="baseYmSelect"></select></label></div>
<section class="metric-grid"><article class="metric"><small>분석 대상 고객</small><strong id="targetCount">-</strong></article><article class="metric danger"><small>고위험 고객</small><strong id="highRiskCount">-</strong></article><article class="metric warning"><small>위험도 상승 고객</small><strong id="increasedCount">-</strong></article><article class="metric"><small>예측 완료율</small><strong id="completionRate">-</strong></article></section>
<section class="split-grid"><article class="panel"><h2>위험등급별 고객 분포</h2><div id="riskDistribution" class="bar-list"></div></article><article class="panel"><h2>예측기간별 평균 위험률</h2><div id="averageRisk" class="bar-list"></div></article></section>
<section class="panel"><div class="panel-title"><h2>고위험 고객</h2><a href="${pageContext.request.contextPath}/customers?riskGrade=WARNING">전체보기</a></div><div class="table-wrap"><table><thead><tr><th>고객번호</th><th>등급</th><th>1개월</th><th>2개월</th><th>3개월</th><th>전월 대비</th><th>주요 요인</th></tr></thead><tbody id="highRiskTable"></tbody></table></div></section>
<p id="pageError" class="error-message" hidden></p></main></div>
<script src="${pageContext.request.contextPath}/js/api.js"></script><script src="${pageContext.request.contextPath}/js/dashboard.js"></script></body></html>

