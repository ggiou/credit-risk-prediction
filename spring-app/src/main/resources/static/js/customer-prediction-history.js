/** 고객 상세 문맥에서 월별 예측 추이와 전체 실행 이력을 표시한다. */
document.addEventListener("DOMContentLoaded", async () => {
    const customerId = document.body.dataset.customerId;
    try {
        const items = await loadAllCustomerHistory(customerId);
        renderCustomerHistoryTrend(items);
        renderCustomerHistoryTable(items);
    } catch (error) {
        BO.showError(error);
    }
});

/** 한 고객의 전체 실행 이력을 API 페이지 단위로 모두 조회한다. */
async function loadAllCustomerHistory(customerId) {
    const baseParams = new URLSearchParams({customerId, size: 100, sort: "predictedAt,desc"});
    const firstPage = await BO.request(`/api/v1/predictions?${baseParams}&page=0`);
    if (firstPage.totalPages <= 1) return firstPage.items;
    const remainingPages = await Promise.all(Array.from(
        {length: firstPage.totalPages - 1},
        (_, index) => BO.request(`/api/v1/predictions?${baseParams}&page=${index + 1}`)
    ));
    return [firstPage, ...remainingPages].flatMap(page => page.items);
}

/** 동일 기준월의 최신 실행만 골라 1·2·3개월 위험률 선 그래프로 표시한다. */
function renderCustomerHistoryTrend(items) {
    const container = document.getElementById("customerHistoryChart");
    const latestByBaseYm = new Map();
    items.forEach(item => {
        if (!latestByBaseYm.has(item.baseYm)) latestByBaseYm.set(item.baseYm, item);
    });
    const months = Array.from(latestByBaseYm.values()).sort((left, right) => left.baseYm.localeCompare(right.baseYm));
    if (!months.length) {
        container.innerHTML = '<div class="trend-empty-state"><span class="trend-info-icon" aria-hidden="true">i</span><p>아직 예측 이력이 없습니다.<br>AI 분석 실행 후 월별 위험률 추이를 확인할 수 있습니다.</p></div>';
        return;
    }

    const series = [
        {key: "hazard1m", label: "1개월", className: "horizon-one"},
        {key: "hazard2m", label: "2개월", className: "horizon-two"},
        {key: "hazard3m", label: "3개월", className: "horizon-three"}
    ];
    const width = Math.max(760, months.length * 92);
    const height = 300;
    const plot = {left: 68, right: 24, top: 22, bottom: 48};
    const plotWidth = width - plot.left - plot.right;
    const plotHeight = height - plot.top - plot.bottom;
    const values = months.flatMap(item => series.map(line => Number(item[line.key]) || 0));
    const maximum = Math.max(...values, 0);
    const ceiling = maximum > 0 ? Math.min(1, Number((maximum * 1.15).toPrecision(2))) : 0.01;
    const x = index => months.length === 1
        ? plot.left + plotWidth / 2
        : plot.left + plotWidth * index / (months.length - 1);
    const y = value => plot.top + plotHeight * (1 - Math.max(0, Math.min(ceiling, value)) / ceiling);
    const gridLines = Array.from({length: 5}, (_, index) => {
        const value = ceiling * (4 - index) / 4;
        const position = plot.top + plotHeight * index / 4;
        return `<line class="history-chart-grid" x1="${plot.left}" y1="${position}" x2="${width - plot.right}" y2="${position}"></line><text class="history-chart-axis-label" x="${plot.left - 10}" y="${position + 4}" text-anchor="end">${BO.escape(BO.percent(value))}</text>`;
    }).join("");
    const monthLabels = months.map((item, index) => `<text class="history-chart-month-label" x="${x(index)}" y="${height - 17}" text-anchor="middle">${BO.escape(formatBaseMonth(item.baseYm))}</text>`).join("");
    const lines = series.map(line => {
        const path = months.map((item, index) => `${index ? "L" : "M"}${x(index)},${y(Number(item[line.key]) || 0)}`).join(" ");
        const points = months.map((item, index) => {
            const value = Number(item[line.key]) || 0;
            return `<circle class="history-chart-point ${line.className}" cx="${x(index)}" cy="${y(value)}" r="4"><title>${BO.escape(formatBaseMonth(item.baseYm))} · ${line.label} ${BO.escape(BO.percent(value))}</title></circle>`;
        }).join("");
        return `<path class="history-chart-line ${line.className}" d="${path}"></path>${points}`;
    }).join("");

    container.innerHTML = `<div class="customer-history-chart-scroll"><svg class="customer-history-chart-svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="기준월별 1개월, 2개월, 3개월 연체 위험률 추이">${gridLines}${monthLabels}${lines}</svg></div>`;
}

/** 모든 실행 결과를 최신순 표로 표시하고 해당 월 AI 분석으로 연결한다. */
function renderCustomerHistoryTable(items) {
    document.getElementById("customerHistoryCount").textContent = `${BO.number(items.length)}건`;
    const table = document.getElementById("customerHistoryTable");
    const basePath = document.body.dataset.customerBasePath;
    table.innerHTML = items.map((item, index) => {
        const params = new URLSearchParams({baseYm: item.baseYm});
        const detailUrl = `${basePath}/${encodeURIComponent(item.customerId)}/ai-analysis?${params}`;
        return `<tr data-history-index="${index}" tabindex="0" aria-label="${BO.escape(formatBaseMonth(item.baseYm))} AI 분석 보기"><td>${BO.koreanDateTime(item.predictedAt)}</td><td>${BO.escape(formatBaseMonth(item.baseYm))}</td><td>${BO.percent(item.hazard1m)}</td><td>${BO.percent(item.hazard2m)}</td><td>${BO.percent(item.hazard3m)}</td><td><span class="badge">${BO.escape(item.riskGradeName)}</span></td><td>${BO.escape(item.modelVersion)}</td><td>${BO.escape(llmStatusName(item.llmStatus))}</td><td><a class="history-detail-link" href="${BO.escape(detailUrl)}">AI 분석 보기</a></td></tr>`;
    }).join("") || '<tr><td colspan="9">예측 이력이 없습니다.</td></tr>';

    table.querySelectorAll("tr[data-history-index]").forEach(row => {
        const open = () => {
            const item = items[Number(row.dataset.historyIndex)];
            const params = new URLSearchParams({baseYm: item.baseYm});
            location.href = `${basePath}/${encodeURIComponent(item.customerId)}/ai-analysis?${params}`;
        };
        row.addEventListener("click", event => { if (!event.target.closest("a")) open(); });
        row.addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            open();
        });
    });
}

/** YYYYMM을 화면용 기준월 형식으로 변환한다. */
function formatBaseMonth(baseYm) {
    const value = String(baseYm || "");
    return /^\d{6}$/.test(value) ? `${value.slice(0, 4)}.${value.slice(4)}` : value || "-";
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
