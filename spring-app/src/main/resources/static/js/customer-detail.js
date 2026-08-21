/** 고객 요약, 금융 데이터, AI 분석 화면을 공통 처리한다. */
document.addEventListener("DOMContentLoaded", async () => {
    const customerId = document.body.dataset.customerId;
    const page = document.body.dataset.page;
    const select = document.getElementById("baseYmSelect");
    try {
        const baseYm = await BO.loadBaseMonths(select);
        const load = () => loadPage(page, customerId, select.value).catch(BO.showError);
        select.addEventListener("change", load);
        if (page === "ai-analysis") document.getElementById("runPrediction").addEventListener("click", () => runPrediction(customerId, select.value).catch(BO.showError));
        await loadPage(page, customerId, baseYm);
    } catch (error) { BO.showError(error); }
});

/** 현재 고객 상세 화면에 맞는 API를 호출한다. */
async function loadPage(page, customerId, baseYm) {
    if (page === "customer-summary") return loadSummary(customerId, baseYm);
    if (page === "customer-financial") return loadFinancial(customerId, baseYm, document.body.dataset.financialType);
    if (page === "ai-analysis") return loadAiAnalysis(customerId, baseYm);
}

/** 고객 요약 지표와 위험률 추이를 표시한다. */
async function loadSummary(customerId, baseYm) {
    const data = await BO.request(`/api/v1/customers/${customerId}/summary?baseYm=${baseYm}`);
    document.getElementById("riskGrade").textContent = data.prediction.riskGradeName || "미분석";
    document.getElementById("hazard1m").textContent = BO.percent(data.prediction.hazard1m);
    document.getElementById("hazard3m").textContent = BO.percent(data.prediction.hazard3m);
    renderDataGrid({...data.cardUsageSummary, ...data.billingSummary, ...data.creditSummary, ...data.balanceSummary});
    document.getElementById("riskTrend").innerHTML = data.riskTrend.map(item => `<div class="bar-row"><span>${item.baseYm}</span><div class="bar-track"><div class="bar-fill" style="width:${item.hazard3m * 100}%"></div></div><strong>${BO.percent(item.hazard3m)}</strong></div>`).join("") || "예측 이력이 없습니다.";
}

/** 선택 금융 탭의 기준월 요약과 월별 표를 표시한다. */
async function loadFinancial(customerId, baseYm, type) {
    const data = await BO.request(`/api/v1/customers/${customerId}/financials/${type}?baseYm=${baseYm}`);
    renderDataGrid(data.summary);
    const keys = data.monthly.length ? Object.keys(data.monthly[0]) : [];
    document.getElementById("financialHead").innerHTML = `<tr>${keys.map(key => `<th>${BO.escape(key)}</th>`).join("")}</tr>`;
    document.getElementById("financialTable").innerHTML = data.monthly.map(row => `<tr>${keys.map(key => `<td>${formatValue(key, row[key])}</td>`).join("")}</tr>`).join("") || '<tr><td>조회 결과가 없습니다.</td></tr>';
}

/** 저장된 현재 AI 분석 결과를 표시한다. */
async function loadAiAnalysis(customerId, baseYm) {
    try { renderPrediction(await BO.request(`/api/v1/customers/${customerId}/predictions/current?baseYm=${baseYm}`)); }
    catch (error) { if (error.status === 404) { document.getElementById("explanation").textContent = "아직 실행된 분석이 없습니다."; return; } throw error; }
}

/** 현재 기준월의 AI 분석을 실행하고 결과를 다시 표시한다. */
async function runPrediction(customerId, baseYm) {
    const button = document.getElementById("runPrediction"); button.disabled = true; button.textContent = "분석 중...";
    try { renderPrediction(await BO.request(`/api/v1/customers/${customerId}/predictions`, {method: "POST", body: JSON.stringify({baseYm, generateExplanation: true})})); }
    finally { button.disabled = false; button.textContent = "AI 분석 실행"; }
}

/** 예측 상세 응답을 위험률, 주요 요인, 설명 영역에 렌더링한다. */
function renderPrediction(data) {
    document.getElementById("hazard1m").textContent = BO.percent(data.risk.hazard1m); document.getElementById("hazard2m").textContent = BO.percent(data.risk.hazard2m); document.getElementById("hazard3m").textContent = BO.percent(data.risk.hazard3m);
    document.getElementById("riskFactors").innerHTML = data.riskFactors.map(item => `<div class="data-item"><small>${BO.escape(item.displayName)}</small><strong>${formatValue(item.unit, item.currentValue)}</strong></div>`).join("") || "주요 위험 요인이 없습니다.";
    document.getElementById("explanation").textContent = data.explanation || (data.llm.status === "FAILED" ? "위험률은 계산됐지만 LLM 설명 생성에 실패했습니다." : "설명 생성이 요청되지 않았습니다.");
    document.getElementById("modelMeta").innerHTML = `<span>모델 ${BO.escape(data.modelVersion)}</span><span>피처 ${BO.escape(data.featureSchemaVersion)}</span><span>LLM ${BO.escape(data.llm.status)}</span>`;
}

/** 객체의 모든 값을 기준월 요약 카드로 표시한다. */
function renderDataGrid(values) { document.getElementById("financialSummary").innerHTML = Object.entries(values).map(([key, value]) => `<div class="data-item"><small>${BO.escape(key)}</small><strong>${formatValue(key, value)}</strong></div>`).join(""); }
/** 필드명과 값 유형에 따라 화면 표시 형식을 정한다. */
function formatValue(key, value) { if (value == null) return "-"; if (typeof value === "boolean") return value ? "예" : "아니오"; if (String(key).toLowerCase().includes("rate") || key === "RATIO") return BO.percent(value); if (typeof value === "number") return BO.number(value); return BO.escape(value); }

