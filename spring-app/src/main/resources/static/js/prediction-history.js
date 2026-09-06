/** 전체 또는 특정 고객의 저장 예측 이력을 검색한다. */
document.addEventListener("DOMContentLoaded", async () => {
    try {
        const baseYmSelect = document.getElementById("baseYmSelect");
        await BO.loadBaseMonths(baseYmSelect, true);
        const query = new URLSearchParams(location.search);
        const customerId = query.get("customerId");
        if (customerId) document.getElementById("customerId").value = customerId;
        document.getElementById("historyForm").addEventListener("submit", event => { event.preventDefault(); searchHistory().catch(BO.showError); }); await searchHistory();
    } catch (error) { BO.showError(error); }
});

/** 현재 검색 조건으로 예측 이력을 조회해 표에 표시한다. */
async function searchHistory() {
    const params = new URLSearchParams({page: 0, size: 50});
    ["customerId", "baseYmSelect", "riskGrade", "llmStatus"].forEach(id => { const value = document.getElementById(id).value.trim(); if (value) params.set(id === "baseYmSelect" ? "baseYm" : id, value); });
    const data = await BO.request(`/api/v1/predictions?${params}`);
    document.getElementById("historyTable").innerHTML = data.items.map(item => `<tr onclick="location.href='/customers/${BO.escape(item.customerId)}/ai-analysis?baseYm=${item.baseYm}'"><td>${BO.koreanDateTime(item.predictedAt)}</td><td>${BO.escape(item.customerId)}</td><td>${item.baseYm}</td><td>${BO.percent(item.hazard1m)}</td><td>${BO.percent(item.hazard2m)}</td><td>${BO.percent(item.hazard3m)}</td><td><span class="badge">${BO.escape(item.riskGradeName)}</span></td><td>${BO.escape(item.modelVersion)}</td><td>${BO.escape(llmStatusName(item.llmStatus))}</td></tr>`).join("") || '<tr><td colspan="9">조회 결과가 없습니다.</td></tr>';
}

/** LLM 처리 상태 코드에 대응하는 한글 표시명을 반환한다. */
function llmStatusName(status) {
    return {
        NOT_REQUESTED: "설명 미요청",
        COMPLETED: "설명 완료",
        FAILED: "설명 실패",
        SKIPPED_NO_EVIDENCE: "설명 근거 없음"
    }[status] || status || "-";
}
