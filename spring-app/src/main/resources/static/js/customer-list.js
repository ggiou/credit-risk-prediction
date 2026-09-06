/** 고객 목록 검색, 페이지 이동, 상세 진입을 처리한다. */
let currentPage = 0;
let lastPage = 0;
let currentSort = "customerId,asc";

document.addEventListener("DOMContentLoaded", async () => {
    try {
        await BO.loadBaseMonths(document.getElementById("baseYmSelect"));
        const query = new URLSearchParams(location.search);
        if (query.get("sort") === "topRiskPercent,asc") currentSort = "topRiskPercent,asc";
        ["customerId", "riskGrade", "analysisStatus"].forEach(id => {
            const value = query.get(id);
            if (!value) return;
            const field = document.getElementById(id);
            field.value = value;
            // 공통 커스텀 드롭다운에도 URL 검색 조건의 선택 상태를 반영한다.
            if (field.tagName === "SELECT") field.dispatchEvent(new Event("change"));
        });
        document.getElementById("searchForm").addEventListener("submit", event => { event.preventDefault(); currentPage = 0; search().catch(BO.showError); });
        document.getElementById("prevPage").addEventListener("click", () => { if (currentPage > 0) { currentPage--; search().catch(BO.showError); } });
        document.getElementById("nextPage").addEventListener("click", () => { if (currentPage + 1 < lastPage) { currentPage++; search().catch(BO.showError); } });
        await search();
    } catch (error) { BO.showError(error); }
});

/** 현재 검색폼 조건으로 고객 페이지를 조회한다. */
async function search() {
    const params = new URLSearchParams({
        baseYm: document.getElementById("baseYmSelect").value,
        page: currentPage,
        size: 20,
        sort: currentSort
    });
    ["customerId", "riskGrade", "analysisStatus"].forEach(id => { const value = document.getElementById(id).value.trim(); if (value) params.set(id, value); });
    const data = await BO.request(`/api/v1/customers?${params}`);
    lastPage = data.totalPages;
    document.getElementById("totalCount").textContent = `${BO.number(data.totalElements)}명`;
    document.getElementById("pageInfo").textContent = `${data.totalPages ? data.page + 1 : 0} / ${data.totalPages}`;
    document.getElementById("customerTable").innerHTML = data.items.map(item => `<tr onclick="location.href='/customers/${BO.escape(item.customerId)}/summary?baseYm=${item.baseYm}'"><td>${BO.escape(item.customerId)}</td><td>${BO.escape(item.displayName || '-')}</td><td>${item.baseYm}</td><td>${BO.escape(analysisStatusName(item.analysisStatus))}</td><td><span class="badge">${BO.escape(item.riskGradeName || '-')}</span></td><td>${BO.percent(item.hazard1m)}</td><td>${BO.percent(item.hazard2m)}</td><td>${BO.percent(item.hazard3m)}</td><td>${BO.escape(modelFeatureLabel(item.primaryRiskFactor))}</td></tr>`).join("") || '<tr><td colspan="9">조회 결과가 없습니다.</td></tr>';
}

/** 구버전 공통 스크립트가 캐시돼 있어도 고객 목록 렌더링을 중단하지 않는다. */
function modelFeatureLabel(value) {
    return typeof BO.modelFeatureLabel === "function" ? BO.modelFeatureLabel(value) : value || "-";
}

/** 분석 상태 코드에 대응하는 한글 표시명을 반환한다. */
function analysisStatusName(status) {
    return {
        NOT_ANALYZED: "미분석",
        OUTDATED: "재분석 필요",
        COMPLETED: "완료",
        PARTIAL: "부분 완료"
    }[status] || status || "-";
}
