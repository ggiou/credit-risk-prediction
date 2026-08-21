/** 대시보드 지표와 고위험 고객을 조회해 렌더링한다. */
document.addEventListener("DOMContentLoaded", async () => {
    const select = document.getElementById("baseYmSelect");
    try { const baseYm = await BO.loadBaseMonths(select); await loadDashboard(baseYm); select.addEventListener("change", () => loadDashboard(select.value).catch(BO.showError)); } catch (error) { BO.showError(error); }
});

/** 선택 기준월의 대시보드 데이터를 표시한다. */
async function loadDashboard(baseYm) {
    const data = await BO.request(`/api/v1/dashboard?baseYm=${baseYm}`);
    document.getElementById("targetCount").textContent = `${BO.number(data.summary.targetCustomerCount)}명`;
    document.getElementById("highRiskCount").textContent = `${BO.number(data.summary.highRiskCustomerCount)}명`;
    document.getElementById("increasedCount").textContent = `${BO.number(data.summary.riskIncreasedCustomerCount)}명`;
    document.getElementById("completionRate").textContent = BO.percent(data.summary.predictionCompletionRate);
    renderBars("riskDistribution", data.riskDistribution.map(item => ({label: item.riskGradeName, value: item.rate})));
    renderBars("averageRisk", data.averageRiskByHorizon.map(item => ({label: `${item.horizon}개월 후`, value: item.riskRate})));
    document.getElementById("highRiskTable").innerHTML = data.highRiskCustomers.map(item => `<tr onclick="location.href='/customers/${BO.escape(item.customerId)}/summary'"><td>${BO.escape(item.customerId)}</td><td><span class="badge">${BO.escape(item.riskGradeName)}</span></td><td>${BO.percent(item.hazard1m)}</td><td>${BO.percent(item.hazard2m)}</td><td>${BO.percent(item.hazard3m)}</td><td>${BO.percent(item.riskChange3m)}</td><td>${BO.escape(item.primaryRiskFactor)}</td></tr>`).join("") || '<tr><td colspan="7">조회 결과가 없습니다.</td></tr>';
}

/** 비율 목록을 가로 막대로 표시한다. */
function renderBars(id, items) { document.getElementById(id).innerHTML = items.map(item => `<div class="bar-row"><span>${BO.escape(item.label)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, item.value * 100)}%"></div></div><strong>${BO.percent(item.value)}</strong></div>`).join(""); }

