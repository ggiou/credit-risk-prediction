<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html>
<html lang="ko">
<head><jsp:include page="../common/head.jsp"/></head>
<body data-page="prediction-batches">
<jsp:include page="../common/sidebar.jsp"/>
<div class="app-shell">
    <jsp:include page="../common/header.jsp"/>
    <main class="batch-admin-main">
        <section id="adminLoginView" class="batch-login-wrap" hidden>
            <div class="batch-login-card">
                <div class="batch-login-brand"><span class="brand-mark"><img src="/images/logo.png" alt="Miribom"></span></div>
                <p class="batch-login-eyebrow">RESTRICTED ACCESS</p>
                <h1>관리자 인증</h1>
                <p class="batch-login-copy">다건 AI 분석은 별도 권한이 필요한 관리자 기능입니다.</p>
                <form id="adminLoginForm" class="batch-login-form">
                    <label>관리자 이메일<input id="adminEmail" type="email" autocomplete="username" placeholder="관리자 이메일을 입력하세요" required></label>
                    <label>비밀번호<input id="adminPassword" type="password" autocomplete="current-password" placeholder="비밀번호를 입력하세요" required></label>
                    <button class="primary" type="submit">관리자 로그인</button>
                </form>
                <p id="loginError" class="error-message" hidden></p>
                <p class="batch-login-note">등록된 관리자 정보는 서버의 비공개 설정에서 확인합니다.</p>
            </div>
        </section>

        <div id="batchDashboard" hidden>
            <div class="page-title batch-page-title">
                <div><p class="page-eyebrow">ADMIN ONLY</p><h1>다건 AI 분석</h1><p>선택한 고객의 LightGBM 예측과 AI 설명을 제한된 동시성으로 처리합니다.</p></div>
                <button id="adminLogout" class="secondary" type="button">로그아웃</button>
            </div>

            <form id="batchSearchForm" class="filter-panel batch-filter-panel">
                <div class="customer-search-with-bulk">
                    <label>고객 검색<input id="batchCustomerQuery" placeholder="고객번호 또는 고객명"></label>
                    <button id="batchBulkSearchTrigger" class="bulk-search-trigger" type="button" aria-label="다량 검색" title="다량 검색">+</button>
                </div>
                <div class="base-month-picker"><label>기준년<select id="baseYearSelect" data-base-year></select></label><label>기준월<select id="baseMonthSelect" data-base-month></select></label><select id="baseYmSelect" hidden aria-hidden="true" tabindex="-1"></select></div>
                <label>위험등급<select id="batchRiskGrade"><option value="">전체</option><option value="NORMAL">정상</option><option value="INTEREST">관심</option><option value="CAUTION">주의</option><option value="WARNING">경고</option></select></label>
                <label>분석 상태<select id="batchAnalysisStatus"><option value="">전체</option><option value="NOT_ANALYZED">미분석</option><option value="OUTDATED">재분석 필요</option><option value="COMPLETED">완료</option><option value="PARTIAL">부분 완료</option></select></label>
                <button class="primary" type="submit">고객 조회</button>
            </form>

            <section class="panel batch-selection-panel">
                <div class="panel-title batch-panel-title"><div><h2>분석 대상 선택</h2><p>한 번에 최대 50명까지 선택할 수 있습니다.</p></div><div class="batch-selection-actions"><strong id="selectedCount">0명 선택</strong><button id="startBatch" class="primary" type="button" disabled>선택 고객 AI 분석</button></div></div>
                <div class="table-wrap batch-customer-table-wrap">
                    <table class="batch-customer-table"><thead><tr><th><input id="selectPage" type="checkbox" aria-label="현재 페이지 전체 선택"></th><th>고객번호</th><th>고객명</th><th>기준월</th><th>분석 상태</th><th>등급</th><th>1개월</th><th>2개월</th><th>3개월</th></tr></thead><tbody id="batchCustomerTable"></tbody></table>
                </div>
                <div class="pagination"><button id="batchPrevPage" type="button">이전</button><span id="batchPageInfo">0 / 0</span><button id="batchNextPage" type="button">다음</button></div>
            </section>

            <section id="batchProgressPanel" class="panel batch-progress-panel" hidden>
                <div class="panel-title batch-panel-title"><div><h2>분석 진행 현황</h2><p id="batchStatusText">작업을 준비하고 있습니다.</p></div><button id="retryFailed" class="secondary" type="button" hidden>실패 항목 재시도</button></div>
                <div class="batch-progress-track"><span id="batchProgressBar"></span></div>
                <div class="batch-progress-metrics">
                    <div><small>전체</small><strong id="batchTotal">0</strong></div><div><small>완료</small><strong id="batchCompleted">0</strong></div><div><small>기존 결과 재사용</small><strong id="batchReused">0</strong></div><div><small>실패</small><strong id="batchFailed">0</strong></div><div><small>대기·처리 중</small><strong id="batchPending">0</strong></div>
                </div>
                <div id="batchFailures" class="batch-failures" hidden><h3>확인이 필요한 항목</h3><ul id="batchFailureList"></ul></div>
            </section>
            <p id="pageError" class="error-message" hidden></p>
        </div>
    </main>
</div>
<jsp:include page="../common/bulk-customer-search-modal.jsp"/>
<script src="${pageContext.request.contextPath}/js/api.js?v=20260906-2"></script>
<script src="${pageContext.request.contextPath}/js/bulk-customer-search.js?v=20260907-1"></script>
<script src="${pageContext.request.contextPath}/js/prediction-batches.js?v=20260907-2"></script>
</body>
</html>
