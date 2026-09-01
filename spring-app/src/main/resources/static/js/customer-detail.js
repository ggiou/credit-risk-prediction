/** 고객 요약, 금융 데이터, AI 분석 화면을 공통 처리한다. */
const FIELD_META = {
    customerId: {label: "비식별 고객번호"},
    displayName: {label: "고객명"},
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

let predictionRequestInFlight = false;

document.addEventListener("DOMContentLoaded", async () => {
    const customerId = document.body.dataset.customerId;
    const page = document.body.dataset.page;
    const select = document.getElementById("baseYmSelect");
    try {
        const baseYm = await BO.loadBaseMonths(select);
        const load = () => {
            syncBaseMonthLinks(select.value);
            return loadPage(page, customerId, select.value).catch(BO.showError);
        };
        select.addEventListener("change", load);
        if (page === "ai-analysis") {
            document.getElementById("runPrediction").addEventListener("click", () => runPrediction(customerId, select.value));
            setupRiskPercentileTooltip();
        }
        syncBaseMonthLinks(baseYm);
        await loadPage(page, customerId, baseYm);
    } catch (error) { BO.showError(error); }
});

/** 현재 고객 상세 화면에 맞는 API를 호출한다. */
async function loadPage(page, customerId, baseYm) {
    if (page === "customer-summary") return loadSummary(customerId, baseYm);
    if (page === "customer-financial") return loadFinancial(customerId, baseYm, document.body.dataset.financialType);
    if (page === "ai-analysis") return loadAiAnalysis(customerId, baseYm);
}

/** 고객 상세 탭을 이동해도 현재 선택한 기준월을 유지한다. */
function syncBaseMonthLinks(baseYm) {
    document.querySelectorAll(".tabs a, .summary-page-action a").forEach(link => {
        const url = new URL(link.href, location.origin);
        if (baseYm) url.searchParams.set("baseYm", baseYm);
        else url.searchParams.delete("baseYm");
        link.href = `${url.pathname}${url.search}`;
    });
}

/** 고객 요약 지표와 위험률 추이를 표시한다. */
async function loadSummary(customerId, baseYm) {
    const data = await BO.request(`/api/v1/customers/${customerId}/summary?baseYm=${baseYm}`);
    renderSummaryStatus(data);
    renderSummaryCustomerInfo(data);
    renderRiskTrend(data.riskTrend);
}

/** 고객 요약을 반복 지표 대신 관리자가 바로 읽을 수 있는 상태 문장과 태그로 표시한다. */
function renderSummaryStatus(data) {
    const customerName = data.customer.displayName || data.customer.customerId || "고객";
    const gradeName = data.prediction.riskGradeName || "미분석";
    const riskPercentile = toRiskPercentile(data.prediction.percentile);
    const riskLevel = riskPercentile == null ? "확인 전" : relativeRiskLevel(riskPercentile).label;
    document.getElementById("summaryCustomerName").textContent = customerName;
    document.getElementById("riskGrade").textContent = data.prediction.riskGradeName ? `${gradeName} 등급` : "미분석 상태";
    document.getElementById("summaryRiskLevel").textContent = riskLevel;
    document.getElementById("customerStatusDescription").textContent = Array.isArray(data.riskTrend) && data.riskTrend.length > 1
        ? "최근 기준월별 예측 결과와 비교한 위험률 추이를 아래에서 확인할 수 있습니다."
        : "최근 비교 가능한 이전 예측 결과는 없습니다.";
    document.getElementById("summaryMemberDelinquency").textContent = `회원 연체 ${booleanCode(data.customer.memberDelinquencyFlag)}`;
    document.getElementById("summaryRecentDelinquency").textContent = `최근 3개월 연체 ${formatCount(data.billingSummary.delinquencyCountR3m, "건")}`;
    document.getElementById("summaryUsedCards").textContent = `이용 카드 ${formatCount(data.cardUsageSummary.usedCreditCardCount, "장")}`;
    document.getElementById("summaryBaseMonth").textContent = `기준월 ${data.baseYm || "-"}`;
    const displayHeading = document.getElementById("customerDisplayHeading");
    const displaySeparator = document.getElementById("customerDisplaySeparator");
    if (displayHeading && displaySeparator && data.customer.displayName) {
        displayHeading.textContent = data.customer.displayName;
        displaySeparator.hidden = false;
    }
}

/** 시안의 2열 핵심 고객 정보를 불필요한 내부 코드와 단위 공백 없이 표시한다. */
function renderSummaryCustomerInfo(data) {
    const items = [
        {label: "연령대", value: data.customer.ageBand},
        {label: "라이프 스테이지", value: stripLifeStageCode(data.customer.lifeStage)},
        {label: "신용카드 가입 경과", value: data.customer.creditMembershipMonths, unit: "개월"},
        {label: "당월 카드 잔액", value: data.balanceSummary.balanceB0m, unit: "원"},
        {label: "최근 3개월 이용금액", value: data.cardUsageSummary.creditUsageAmountR3m, unit: "원"},
        {label: "신용카드 이용한도", value: data.creditSummary.creditLimitAmount, unit: "원"}
    ];
    document.getElementById("customerInfo").innerHTML = items.map(item => `
        <div class="data-item"><small>${BO.escape(item.label)}</small><strong>${formatCompactValue(item.value, item.unit)}</strong></div>`).join("");
}

/** 라이프 스테이지의 분류용 숫자 접두사는 관리자 화면에서 숨긴다. */
function stripLifeStageCode(value) {
    return value == null ? null : String(value).replace(/^\d+\./, "");
}

/** 시안처럼 숫자와 원·건·개월 단위를 붙여 표시한다. */
function formatCompactValue(value, unit = "") {
    if (value == null || value === "") return "-";
    if (typeof value === "number") return `${BO.number(value)}${unit}`;
    return BO.escape(value);
}

/** 요약 태그의 건수 값을 표시한다. */
function formatCount(value, unit) {
    return value == null ? "-" : `${BO.number(value)}${unit}`;
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
    const data = await BO.request(`/api/v1/customers/${customerId}/predictions/current?baseYm=${baseYm}`);
    if (data == null) {
        renderEmptyPrediction();
        return;
    }
    renderPrediction(data);
}

/** 현재 기준월의 AI 분석을 실행하고 결과를 다시 표시한다. */
async function runPrediction(customerId, baseYm) {
    if (predictionRequestInFlight) return;
    predictionRequestInFlight = true;
    setPredictionLoading(true);
    clearPageError();
    try {
        renderPrediction(await BO.request(`/api/v1/customers/${customerId}/predictions`, {
            method: "POST",
            body: JSON.stringify({baseYm, generateExplanation: true})
        }));
    } catch (error) {
        BO.showError(error);
    } finally {
        predictionRequestInFlight = false;
        setPredictionLoading(false);
    }
}

/** AI 요청 중 화면 조작을 막고 진행 상태를 표시한다. */
function setPredictionLoading(loading) {
    const button = document.getElementById("runPrediction");
    const select = document.getElementById("baseYmSelect");
    const overlay = document.getElementById("predictionLoading");
    button.disabled = loading;
    button.textContent = loading ? "분석 중..." : "AI 분석 실행";
    select.disabled = loading;
    overlay.hidden = !loading;
    document.body.classList.toggle("is-loading", loading);
}

/** 이전 요청의 오류 문구를 새 분석 실행 전에 지운다. */
function clearPageError() {
    const element = document.getElementById("pageError");
    if (!element) return;
    element.textContent = "";
    element.hidden = true;
}

/** 예측 상세 응답을 위험률, 주요 요인, 설명 영역에 렌더링한다. */
function renderPrediction(data) {
    setPredictionResultVisible(true);
    renderHazards(data.risk);
    document.getElementById("predictionRiskGrade").textContent = data.risk.riskGradeName || "-";
    renderRiskPercentile(data.risk.percentile);
    renderRiskFactors(data.riskFactors);
    renderExplanation(data.explanation, data.llm.status);
    document.getElementById("modelMeta").innerHTML = `<span>모델 ${BO.escape(data.modelVersion)}</span><span>피처 ${BO.escape(data.featureSchemaVersion)}</span><span>LLM ${BO.escape(llmStatusName(data.llm.status))}</span>`;
}

/** 분석하지 않은 기준월로 이동했을 때 이전 월 결과를 모두 비운다. */
function renderEmptyPrediction() {
    setPredictionResultVisible(false);
}

/** 미분석 기준월에는 빈 결과 카드 대신 분석 전 안내만 표시한다. */
function setPredictionResultVisible(available) {
    document.getElementById("predictionEmptyState").hidden = available;
    document.getElementById("predictionResult").hidden = !available;
}

/** LLM의 줄 단위 설명을 HTML 문자열로 신뢰하지 않고 안전한 목록으로 렌더링한다. */
function renderExplanation(explanation, status, emptyMessage) {
    const container = document.getElementById("explanation");
    const intro = document.getElementById("explanationIntro");
    const note = document.getElementById("explanationNote");
    const lines = explanation == null ? [] : String(explanation)
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(Boolean);
    const available = lines.length > 0;

    intro.hidden = !available;
    note.hidden = !available;
    container.classList.toggle("explanation-empty", !available);
    if (!available) {
        container.textContent = emptyMessage || (status === "FAILED"
            ? "위험률은 계산됐지만 AI 설명 생성에 실패했습니다."
            : "설명 생성이 요청되지 않았습니다.");
        return;
    }

    const structured = lines.length >= 3 && !/^[-•]\s*/.test(lines[0]);
    if (!structured) {
        container.innerHTML = `<ul class="explanation-list">${lines
            .map(line => `<li>${BO.escape(line.replace(/^[-•]\s*/, ""))}</li>`)
            .join("")}</ul>`;
        return;
    }

    const summary = lines[0];
    const interpretation = lines[lines.length - 1];
    const changes = lines.slice(1, -1).map(line => line.replace(/^[-•]\s*/, ""));
    container.innerHTML = `
        <p class="explanation-summary">${BO.escape(summary)}</p>
        <h3 class="explanation-subtitle">주요 변화</h3>
        <ul class="explanation-list">${changes.map(item => `<li>${BO.escape(item)}</li>`).join("")}</ul>
        <div class="explanation-interpretation"><strong>모델 해석</strong><p>${BO.escape(interpretation)}</p></div>`;
}

/** 월별 위험률 값과 세 기간 내 상대적인 막대 길이를 표시한다. */
function renderHazards(risk) {
    const hazards = [risk.hazard1m, risk.hazard2m, risk.hazard3m].map(value =>
        value == null || value === "" ? null : Number(value));
    ["hazard1m", "hazard2m", "hazard3m"].forEach((id, index) => {
        const value = hazards[index];
        document.getElementById(id).textContent = value == null || !Number.isFinite(value) ? "-" : BO.percent(value);
    });
    const finiteHazards = hazards.filter(value => Number.isFinite(value) && value >= 0);
    const maximum = finiteHazards.length ? Math.max(...finiteHazards) : 0;
    const comparisonCeiling = maximum > 0
        ? Math.min(1, Number((maximum * 1.2).toPrecision(2)))
        : 0;
    ["hazard1mBar", "hazard2mBar", "hazard3mBar"].forEach((id, index) => {
        const value = hazards[index];
        const width = comparisonCeiling > 0 && Number.isFinite(value) && value > 0
            ? Math.max(4, Math.min(100, value / comparisonCeiling * 100))
            : 0;
        document.getElementById(id).style.width = `${width}%`;
    });
    document.getElementById("hazardScaleMaximum").textContent = comparisonCeiling > 0
        ? BO.percent(comparisonCeiling)
        : "-";
}

/** 모델의 상위 위험 백분율을 낮은 위험부터 세는 일반 백분위로 변환해 표시한다. */
function renderRiskPercentile(value) {
    const riskPercentile = toRiskPercentile(value);
    const label = document.getElementById("riskPercentile");
    const level = document.getElementById("riskPercentileLevel");
    const tooltip = document.getElementById("riskPercentileTooltip");
    const marker = document.getElementById("riskPercentileMarker");
    if (riskPercentile == null) {
        label.textContent = "-";
        level.textContent = "-";
        level.className = "risk-level risk-level-neutral";
        marker.hidden = true;
        tooltip.textContent = "상대적 위험 위치를 표시할 수 없습니다. 실제 연체 확률이 아닙니다.";
        return;
    }
    const formatted = riskPercentile.toLocaleString("ko-KR", {maximumFractionDigits: 1});
    const relativeLevel = relativeRiskLevel(riskPercentile);
    label.textContent = `${formatted} 백분위`;
    level.textContent = relativeLevel.label;
    level.className = `risk-level ${relativeLevel.className}`;
    marker.hidden = false;
    marker.style.left = `${riskPercentile}%`;
    tooltip.textContent = `위험도가 낮은 고객부터 비교한 상대적 위치입니다. 이 고객보다 위험도가 낮거나 같은 고객이 약 ${formatted}%입니다. 실제 연체 확률이 아닙니다.`;
}

/** 모델의 고위험 순위 백분율을 화면용 일반 위험 백분위로 변환한다. */
function toRiskPercentile(value) {
    const upperRiskPercentile = Number(value);
    if (value == null || value === "" || !Number.isFinite(upperRiskPercentile)
            || upperRiskPercentile < 0 || upperRiskPercentile > 100) return null;
    return 100 - upperRiskPercentile;
}

/** 상대 위험 백분위를 사분위 기준의 직관적인 세 구간으로 요약한다. */
function relativeRiskLevel(percentile) {
    if (percentile < 25) return {label: "낮은 편", className: "risk-level-low"};
    if (percentile < 75) return {label: "평균 수준", className: "risk-level-medium"};
    return {label: "높은 편", className: "risk-level-high"};
}

/** 백분위 설명을 마우스, 키보드, 터치에서 동일하게 열고 닫는다. */
function setupRiskPercentileTooltip() {
    const card = document.getElementById("riskPercentileCard");
    const button = document.getElementById("riskPercentileInfo");
    if (!card || !button) return;
    const close = () => {
        card.classList.remove("is-tooltip-open");
        button.setAttribute("aria-expanded", "false");
    };
    button.addEventListener("click", event => {
        event.stopPropagation();
        const open = card.classList.toggle("is-tooltip-open");
        button.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", event => { if (!card.contains(event.target)) close(); });
    document.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
}

/** 월별 예측이 두 건 이상일 때만 3개월 후 위험률의 비교 추이를 그린다. */
function renderRiskTrend(items) {
    const container = document.getElementById("riskTrend");
    if (!Array.isArray(items) || items.length === 0) {
        container.innerHTML = '<div class="trend-empty-state"><span class="trend-info-icon" aria-hidden="true">i</span><p>아직 예측 결과가 없습니다.<br>AI 분석 실행 후 위험률 추이를 확인할 수 있습니다.</p></div>';
        return;
    }
    if (items.length === 1) {
        container.innerHTML = '<div class="trend-empty-state"><span class="trend-info-icon" aria-hidden="true">i</span><p>비교할 이전 예측 결과가 없습니다.<br>다음 기준월 예측부터 변화 추이를 확인할 수 있습니다.</p></div>';
        return;
    }
    container.innerHTML = items.map(item => `<div class="bar-row"><span>${item.baseYm}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, Math.max(0, item.hazard3m * 100))}%"></div></div><strong>${BO.percent(item.hazard3m)}</strong></div>`).join("");
}

/** 신규·기존 예측 결과 모두 모델 피처 키 대신 화면용 한글명을 사용한다. */
function riskFactorLabel(item) {
    const fallback = item.displayName || item.featureKey || "-";
    return typeof BO.modelFeatureLabel === "function" ? BO.modelFeatureLabel(item.featureKey, fallback) : fallback;
}

/** 주요 지표를 영향 순서와 이전·현재 값 변화가 드러나는 목록으로 표시한다. */
function renderRiskFactors(items) {
    const container = document.getElementById("riskFactors");
    if (!Array.isArray(items) || items.length === 0) {
        container.innerHTML = '<p class="empty-state">모델 판단에 영향을 준 주요 지표가 없습니다.</p>';
        return;
    }
    container.innerHTML = items.map((item, index) => `
        <div class="risk-factor-row">
            <span class="risk-factor-rank">${index + 1}</span>
            <strong class="risk-factor-name">${BO.escape(riskFactorLabel(item))}</strong>
            <span class="risk-factor-value risk-factor-previous"><small>이전</small>${formatRiskFactorValue(item, item.previousValue)}</span>
            <span class="risk-factor-arrow" aria-hidden="true">→</span>
            <span class="risk-factor-value risk-factor-current"><small>현재</small>${formatRiskFactorValue(item, item.currentValue)}</span>
            <span class="risk-factor-change">${formatRiskFactorChange(item)}</span>
        </div>`).join("");
}

/** 모델 피처별 금액·건수·비율 단위를 적용한다. */
function formatRiskFactorValue(item, value = item.currentValue) {
    const meta = typeof BO.modelFeatureMeta === "function" ? BO.modelFeatureMeta(item.featureKey) : null;
    if (value == null) return "-";
    if (meta?.type === "boolean") return booleanCode(value);
    if (meta?.type === "percentagePoint") return `${BO.number(value)}%`;
    if (meta?.type === "ratio" || item.unit === "RATIO") return BO.percent(value);
    if (typeof value === "number") return `${BO.number(value)}${meta?.unit ? ` ${meta.unit}` : ""}`;
    return BO.escape(value);
}

/** 주요 지표의 전월 대비 변화를 값 변화와 모델 기여 방향을 혼동하지 않도록 표시한다. */
function formatRiskFactorChange(item) {
    if (item.previousValue == null || item.currentValue == null) return "이전값 없음";
    const changeRate = Number(item.changeRate);
    if (Number.isFinite(changeRate)) {
        const percent = Math.abs(changeRate * 100).toLocaleString("ko-KR", {maximumFractionDigits: 1});
        if (changeRate > 0) return `+${percent}%`;
        if (changeRate < 0) return `-${percent}%`;
        return "변동 없음";
    }
    return String(item.previousValue) === String(item.currentValue) ? "변동 없음" : "값 변경";
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
    if (meta?.type === "boolean" || typeof value === "boolean") return booleanCode(value);
    if (meta?.type === "percentagePoint") return `${BO.number(value)}%`;
    if (key === "RATIO") return BO.percent(value);
    if (typeof value === "number") return `${BO.number(value)}${meta?.unit ? ` ${meta.unit}` : ""}`;
    return BO.escape(value);
}

/** DB와 API의 Boolean 표현을 화면용 Y/N 코드로 통일한다. */
function booleanCode(value) {
    if (value == null || value === "") return "-";
    return value === true || value === 1 || value === "1" || String(value).toUpperCase() === "Y" ? "Y" : "N";
}
