/** 고객 요약, 금융 데이터, AI 분석 화면을 공통 처리한다. */
const FIELD_META = {
    customerId: {label: "비식별 고객번호"},
    baseYm: {label: "기준월"},
    ageBand: {label: "연령대"},
    lifeStage: {label: "라이프 스테이지"},
    creditMembershipMonths: {label: "신용카드 가입 경과", unit: "개월"},
    validCreditCardCount: {label: "유효 신용카드 수", unit: "장"},
    availableCreditCardCount: {label: "이용 가능 신용카드 수", unit: "장"},
    usedCreditCardCount: {label: "이용 신용카드 수", unit: "장"},
    creditUsageAmountR3m: {label: "최근 3개월 신용카드 이용금액", unit: "원"},
    memberDelinquencyFlag: {label: "회원 연체 여부", type: "boolean"},
    billedAmountB0: {label: "당월 청구금액", unit: "원"},
    billedAmountR3m: {label: "최근 3개월 청구금액", unit: "원"},
    delinquencyCountR3m: {label: "최근 3개월 연체 건수", unit: "건"},
    delinquencyCountR6m: {label: "최근 6개월 연체 건수", unit: "건"},
    onDueDatePaymentMonthCountR3m: {label: "최근 3개월 결제일 상환 개월 수", unit: "개월"},
    prepaymentCountR3m: {label: "최근 3개월 선결제 건수", unit: "건"},
    creditLimitAmount: {label: "신용카드 이용한도", unit: "원"},
    cashAdvanceLimitAmount: {label: "현금서비스 한도", unit: "원"},
    creditLimitAmountB1m: {label: "전월 신용카드 이용한도", unit: "원"},
    forcedLimitReductionCountR12m: {label: "최근 12개월 강제 한도 감액 횟수", unit: "회"},
    forcedLimitReductionAmountR12m: {label: "최근 12개월 강제 한도 감액금액", unit: "원"},
    voluntaryLimitReductionCountR12m: {label: "최근 12개월 자발적 한도 감액 횟수", unit: "회"},
    limitIncreaseCountR12m: {label: "최근 12개월 한도 증액 횟수", unit: "회"},
    limitReviewRequestCount: {label: "한도 심사 요청 건수", unit: "건"},
    limitRequestRejectionCount: {label: "한도 요청 거절 건수", unit: "건"},
    marketShortDelinquencyFlagR3m: {label: "최근 3개월 시장 단기연체 여부", type: "boolean"},
    marketShortDelinquencyFlagR6m: {label: "최근 6개월 시장 단기연체 여부", type: "boolean"},
    revolvingAgreedBillingRate: {label: "리볼빙 약정 청구율", type: "percentagePoint"},
    balanceB0m: {label: "당월 카드 잔액", unit: "원"},
    lumpSumBalanceB0m: {label: "당월 일시불 잔액", unit: "원"},
    installmentBalanceB0m: {label: "당월 할부 잔액", unit: "원"},
    cashAdvanceBalanceB0m: {label: "당월 현금서비스 잔액", unit: "원"},
    cardLoanBalanceB0m: {label: "당월 카드론 잔액", unit: "원"},
    revolvingCarryoverBalanceB0m: {label: "당월 리볼빙 일시불 이월잔액", unit: "원"},
    cashAdvanceBalanceB1m: {label: "전월 현금서비스 잔액", unit: "원"},
    cardLoanBalanceB1m: {label: "전월 카드론 잔액", unit: "원"},
    monthlyAverageBalance: {label: "월중 평균잔액", unit: "원"}
};

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
    renderDataGrid({
        customerId: data.customer.customerId,
        baseYm: data.baseYm,
        ageBand: data.customer.ageBand,
        lifeStage: data.customer.lifeStage,
        creditMembershipMonths: data.customer.creditMembershipMonths,
        memberDelinquencyFlag: data.customer.memberDelinquencyFlag
    }, "customerInfo");
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
    document.getElementById("financialHead").innerHTML = `<tr>${keys.map(key => `<th>${BO.escape(fieldLabel(key))}</th>`).join("")}</tr>`;
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
    document.getElementById("modelMeta").innerHTML = `<span>모델 ${BO.escape(data.modelVersion)}</span><span>피처 ${BO.escape(data.featureSchemaVersion)}</span><span>LLM ${BO.escape(llmStatusName(data.llm.status))}</span>`;
}

/** 객체의 모든 값을 기준월 요약 카드로 표시한다. */
function renderDataGrid(values, elementId = "financialSummary") { document.getElementById(elementId).innerHTML = Object.entries(values).map(([key, value]) => `<div class="data-item"><small>${BO.escape(fieldLabel(key))}</small><strong>${formatValue(key, value)}</strong></div>`).join(""); }
/** API 필드명에 대응하는 화면용 한글명을 반환한다. */
function fieldLabel(key) { return FIELD_META[key]?.label || key; }
/** LLM 처리 상태 코드에 대응하는 한글 표시명을 반환한다. */
function llmStatusName(status) {
    return {
        NOT_REQUESTED: "설명 미요청",
        COMPLETED: "설명 완료",
        FAILED: "설명 실패"
    }[status] || status || "-";
}
/** 필드명과 값 유형에 따라 화면 표시 형식을 정한다. */
function formatValue(key, value) {
    if (value == null) return "-";
    const meta = FIELD_META[key];
    if (meta?.type === "boolean" || typeof value === "boolean") return Number(value) === 1 ? "예" : "아니오";
    if (meta?.type === "percentagePoint") return `${BO.number(value)}%`;
    if (key === "RATIO") return BO.percent(value);
    if (typeof value === "number") return `${BO.number(value)}${meta?.unit ? ` ${meta.unit}` : ""}`;
    return BO.escape(value);
}
