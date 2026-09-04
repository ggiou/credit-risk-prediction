/** 대시보드 지표와 고위험 고객을 조회해 렌더링한다. */
document.addEventListener("DOMContentLoaded", async () => {
    const select = document.getElementById("baseYmSelect");
    try { const baseYm = await BO.loadBaseMonths(select); await loadDashboard(baseYm); select.addEventListener("change", () => loadDashboard(select.value).catch(BO.showError)); } catch (error) { BO.showError(error); }
});

/** 선택 기준월의 대시보드 데이터를 표시한다. */
async function loadDashboard(baseYm) {
    const data = await BO.request(`/api/v1/dashboard?baseYm=${baseYm}`);
    updateHighRiskViewAllLink(data.baseYm);
    document.getElementById("targetCount").textContent = `${BO.number(data.summary.targetCustomerCount)}명`;
    document.getElementById("highRiskCount").textContent = `${BO.number(data.summary.highRiskCustomerCount)}명`;
    document.getElementById("increasedCount").textContent = `${BO.number(data.summary.riskIncreasedCustomerCount)}명`;
    document.getElementById("completionRate").textContent = BO.percent(data.summary.predictionCompletionRate);
    renderRatioBars("riskDistribution", data.riskDistribution.map(item => ({label: item.riskGradeName, value: item.rate})));
    renderExpandedRiskBars("averageRisk", data.averageRiskByHorizon.map(item => ({label: `${item.horizon}개월 후`, value: item.riskRate})));
    document.getElementById("highRiskTable").innerHTML = data.highRiskCustomers.map(item => `<tr onclick="location.href='/customers/${BO.escape(item.customerId)}/summary'"><td>${BO.escape(item.customerId)}</td><td><span class="badge">${BO.escape(item.riskGradeName)}</span></td><td>${BO.percent(item.hazard1m)}</td><td>${BO.percent(item.hazard2m)}</td><td>${BO.percent(item.hazard3m)}</td><td>${BO.percent(item.riskChange3m)}</td><td>${BO.escape(modelFeatureLabel(item.primaryRiskFactor))}</td></tr>`).join("") || '<tr><td colspan="7">조회 결과가 없습니다.</td></tr>';
}

/** 현재 대시보드 기준월, 경고 등급, 모델 종합 위험 순서를 고객 전체보기 링크에 유지한다. */
function updateHighRiskViewAllLink(baseYm) {
    const link = document.getElementById("highRiskViewAll");
    if (!link) return;
    const params = new URLSearchParams({
        baseYm,
        riskGrade: "WARNING",
        sort: "topRiskPercent,asc"
    });
    link.href = `${link.dataset.customerListPath}?${params}`;
}

/** 구버전 공통 스크립트가 캐시돼 있어도 대시보드 렌더링을 중단하지 않는다. */
function modelFeatureLabel(value) {
    return typeof BO.modelFeatureLabel === "function" ? BO.modelFeatureLabel(value) : value || "-";
}

/** 비율 목록을 가로 막대로 표시한다. */
function renderRatioBars(id, items) { document.getElementById(id).innerHTML = items.map(item => `<div class="bar-row"><span>${BO.escape(item.label)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, item.value * 100)}%"></div></div><strong>${BO.percent(item.value)}</strong></div>`).join(""); }

/** 매우 작은 평균 위험률 세 값의 차이를 패널 내 확대 막대로 표시한다. */
function renderExpandedRiskBars(id, items) {
    const values = items.map(item => Number(item.value));
    const finiteValues = values.filter(value => Number.isFinite(value) && value >= 0);
    const maximum = finiteValues.length ? Math.max(...finiteValues) : 0;
    const comparisonCeiling = maximum > 0
        ? Math.min(1, Number((maximum * 1.2).toPrecision(2)))
        : 0;
    document.getElementById(id).innerHTML = items.map((item, index) => {
        const value = values[index];
        const width = comparisonCeiling > 0 && Number.isFinite(value) && value > 0
            ? Math.max(4, Math.min(100, value / comparisonCeiling * 100))
            : 0;
        const label = Number.isFinite(value) ? BO.percent(value) : "-";
        return `<div class="hazard-bar-row"><span>${BO.escape(item.label)}</span><div class="hazard-track"><div class="hazard-fill" style="width:${width}%"></div></div><strong>${label}</strong></div>`;
    }).join("");
    document.getElementById("dashboardRiskScaleMaximum").textContent = comparisonCeiling > 0
        ? BO.percent(comparisonCeiling)
        : "-";
}
