/** 공통 API 호출과 화면 표시 유틸리티를 제공한다. */
const BO = (() => {
    const customSelects = new WeakMap();
    let customSelectSequence = 0;
    let customSelectDocumentEventsBound = false;
    const MODEL_FEATURE_META = {
        남녀구분코드: {label: "성별"},
        연령: {label: "연령대"},
        입회경과개월수_신용: {label: "신용카드 가입 경과 개월 수", unit: "개월"},
        회원여부_연체: {label: "회원 연체 여부", type: "boolean"},
        유효카드수_신용: {label: "유효 신용카드 수", unit: "장"},
        이용가능카드수_신용: {label: "이용 가능 신용카드 수", unit: "장"},
        이용카드수_신용: {label: "이용 신용카드 수", unit: "장"},
        이용금액_R3M_신용: {label: "최근 3개월 신용카드 이용금액", unit: "원"},
        Life_Stage: {label: "라이프 스테이지"},
        카드이용한도금액: {label: "카드 이용한도", unit: "원"},
        CA한도금액: {label: "현금서비스 이용한도", unit: "원"},
        RV약정청구율: {label: "리볼빙 약정 청구율", type: "percentagePoint"},
        자발한도감액횟수_R12M: {label: "최근 12개월 자발적 한도 감액 횟수", unit: "회"},
        강제한도감액횟수_R12M: {label: "최근 12개월 강제 한도 감액 횟수", unit: "회"},
        강제한도감액금액_R12M: {label: "최근 12개월 강제 한도 감액금액", unit: "원"},
        한도증액횟수_R12M: {label: "최근 12개월 한도 증액 횟수", unit: "회"},
        카드이용한도금액_B1M: {label: "전월 카드 이용한도", unit: "원"},
        한도심사요청건수: {label: "한도 심사 요청 건수", unit: "건"},
        한도요청거절건수: {label: "한도 요청 거절 건수", unit: "건"},
        시장단기연체여부_R6M: {label: "최근 6개월 시장 단기연체 여부", type: "boolean"},
        시장단기연체여부_R3M: {label: "최근 3개월 시장 단기연체 여부", type: "boolean"},
        청구금액_B0: {label: "기준월 청구금액", unit: "원"},
        청구금액_R3M: {label: "최근 3개월 청구금액", unit: "원"},
        상환개월수_결제일_R3M: {label: "최근 3개월 결제일 상환 개월 수", unit: "개월"},
        선결제건수_R3M: {label: "최근 3개월 선결제 건수", unit: "건"},
        연체건수_R6M: {label: "최근 6개월 연체 건수", unit: "건"},
        연체건수_R3M: {label: "최근 3개월 연체 건수", unit: "건"},
        잔액_B0M: {label: "기준월 총 카드 잔액", unit: "원"},
        잔액_일시불_B0M: {label: "기준월 일시불 잔액", unit: "원"},
        잔액_할부_B0M: {label: "기준월 할부 잔액", unit: "원"},
        잔액_현금서비스_B0M: {label: "기준월 현금서비스 잔액", unit: "원"},
        잔액_리볼빙일시불이월_B0M: {label: "기준월 리볼빙 일시불 이월잔액", unit: "원"},
        잔액_카드론_B0M: {label: "기준월 카드론 잔액", unit: "원"},
        잔액_현금서비스_B1M: {label: "전월 현금서비스 잔액", unit: "원"},
        잔액_카드론_B1M: {label: "전월 카드론 잔액", unit: "원"},
        월중평잔: {label: "월중 평균잔액", unit: "원"},
        f_사용률: {label: "카드 한도 사용률", type: "ratio"},
        f_현금서비스비중: {label: "현금서비스 비중", type: "ratio"},
        f_카드론비중: {label: "카드론 비중", type: "ratio"},
        f_리볼빙비중: {label: "리볼빙 비중", type: "ratio"},
        f_현금서비스증가: {label: "현금서비스 잔액 증가", unit: "원"},
        f_카드론증가: {label: "카드론 잔액 증가", unit: "원"},
        f_한도변화: {label: "카드 이용한도 변화", unit: "원"},
        f_잔액증가율: {label: "총잔액 증가율", type: "ratio"},
        f_사용률변화: {label: "카드 한도 사용률 변화", type: "ratio"},
        f_청구금액증가: {label: "청구금액 증가", unit: "원"},
        f_카드가용비율: {label: "이용 가능 카드 비율", type: "ratio"}
    };

    /** JSON API를 호출하고 공통 오류 응답을 예외로 변환한다. */
    async function request(path, options = {}) {
        const response = await fetch(path, {headers: {"Accept": "application/json", "Content-Type": "application/json", ...(options.headers || {})}, ...options});
        if (response.status === 204) return null;
        const body = await response.json().catch(() => ({}));
        if (!response.ok || body.success === false) {
            // 서버 오류의 안전한 사용자 메시지만 화면 코드로 전달한다.
            const detailMessage = typeof body.detail === "string" ? body.detail : body.detail?.message;
            const error = new Error(body.error?.message || detailMessage || "요청 처리에 실패했습니다.");
            error.code = body.error?.code || body.detail?.code;
            error.status = response.status;
            error.requestId = body.requestId || response.headers.get("X-Request-Id");
            throw error;
        }
        return body.data ?? body;
    }

    /** 기준년월 선택 상자를 실제 적재월로 채운다. */
    async function loadBaseMonths(select, includeAll = false) {
        if (!select) return null;
        const data = await request("/api/v1/meta/base-months");
        const queryBaseYm = new URLSearchParams(location.search).get("baseYm");
        const selected = queryBaseYm || (includeAll ? "" : data.defaultBaseYm);
        select.innerHTML = includeAll ? '<option value="">전체</option>' : "";
        data.baseMonths.forEach(month => select.add(new Option(month, month, false, month === selected)));

        const picker = select.closest(".base-month-picker");
        const yearSelect = picker?.querySelector("[data-base-year]");
        const monthSelect = picker?.querySelector("[data-base-month]");
        if (!yearSelect || !monthSelect) return selected;

        const monthsByYear = data.baseMonths.reduce((groups, baseYm) => {
            const year = baseYm.slice(0, 4);
            (groups[year] ||= []).push(baseYm);
            return groups;
        }, {});
        const years = Object.keys(monthsByYear).sort((left, right) => right.localeCompare(left));
        yearSelect.innerHTML = includeAll ? '<option value="">전체</option>' : "";
        years.forEach(year => yearSelect.add(new Option(`${year}년`, year)));

        const populateMonths = (year, preferredBaseYm) => {
            monthSelect.innerHTML = "";
            if (!year) {
                monthSelect.add(new Option("전체", ""));
                monthSelect.disabled = true;
                select.value = "";
                refreshCustomSelect(monthSelect);
                return;
            }
            monthSelect.disabled = false;
            (monthsByYear[year] || []).forEach(baseYm => {
                const month = baseYm.slice(4, 6);
                monthSelect.add(new Option(`${Number(month)}월`, baseYm, false, baseYm === preferredBaseYm));
            });
            select.value = monthSelect.value;
            refreshCustomSelect(monthSelect);
        };
        const selectedYear = selected ? selected.slice(0, 4) : "";
        yearSelect.value = selectedYear;
        populateMonths(selectedYear, selected);

        const notifyChange = () => select.dispatchEvent(new Event("change"));
        yearSelect.addEventListener("change", () => {
            populateMonths(yearSelect.value, "");
            notifyChange();
        });
        monthSelect.addEventListener("change", () => {
            select.value = monthSelect.value;
            notifyChange();
        });
        enhanceSelects();
        return select.value;
    }

    /** 모든 기본 select를 기존 값과 이벤트를 유지하는 사이트 공통 드롭다운으로 꾸민다. */
    function enhanceSelects(root = document) {
        root.querySelectorAll("select:not([hidden])").forEach(enhanceSelect);
        if (customSelectDocumentEventsBound) return;
        customSelectDocumentEventsBound = true;
        document.addEventListener("click", event => {
            document.querySelectorAll(".custom-select.is-open").forEach(wrapper => {
                if (!wrapper.contains(event.target)) closeCustomSelect(wrapper);
            });
        });
        document.addEventListener("keydown", event => {
            if (event.key !== "Escape") return;
            document.querySelectorAll(".custom-select.is-open").forEach(closeCustomSelect);
        });
    }

    /** 단일 select에 커스텀 트리거와 스크롤 가능한 옵션 메뉴를 연결한다. */
    function enhanceSelect(select) {
        if (customSelects.has(select)) {
            refreshCustomSelect(select);
            return;
        }
        const wrapper = document.createElement("div");
        wrapper.className = "custom-select";
        const trigger = document.createElement("button");
        trigger.type = "button";
        trigger.className = "custom-select-trigger";
        trigger.setAttribute("aria-haspopup", "listbox");
        trigger.setAttribute("aria-expanded", "false");
        const value = document.createElement("span");
        value.className = "custom-select-value";
        const menu = document.createElement("div");
        menu.className = "custom-select-menu";
        menu.id = `customSelectMenu${++customSelectSequence}`;
        menu.setAttribute("role", "listbox");
        menu.hidden = true;
        trigger.setAttribute("aria-controls", menu.id);
        trigger.append(value);
        wrapper.append(trigger, menu);
        select.classList.add("native-select-hidden");
        select.setAttribute("aria-hidden", "true");
        select.tabIndex = -1;
        select.insertAdjacentElement("afterend", wrapper);
        const labelText = Array.from(select.closest("label")?.childNodes || [])
            .filter(node => node.nodeType === Node.TEXT_NODE)
            .map(node => node.textContent.trim())
            .find(Boolean) || "선택";
        customSelects.set(select, {wrapper, trigger, value, menu, labelText});

        trigger.addEventListener("click", event => {
            event.stopPropagation();
            if (wrapper.classList.contains("is-open")) {
                closeCustomSelect(wrapper);
                return;
            }
            document.querySelectorAll(".custom-select.is-open").forEach(closeCustomSelect);
            wrapper.classList.add("is-open");
            trigger.setAttribute("aria-expanded", "true");
            menu.hidden = false;
        });
        trigger.addEventListener("keydown", event => {
            if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
            event.preventDefault();
            if (!wrapper.classList.contains("is-open")) trigger.click();
            const selectedOption = menu.querySelector('[aria-selected="true"]');
            (selectedOption || menu.querySelector("button:not(:disabled)"))?.focus();
        });
        select.addEventListener("change", () => refreshCustomSelect(select));
        refreshCustomSelect(select);
    }

    /** 원본 option 변경과 선택 상태를 커스텀 메뉴에 동기화한다. */
    function refreshCustomSelect(select) {
        const custom = customSelects.get(select);
        if (!custom) return;
        const selectedOption = select.options[select.selectedIndex];
        custom.value.textContent = selectedOption?.textContent || "선택";
        custom.trigger.disabled = select.disabled;
        custom.trigger.setAttribute("aria-label", `${custom.labelText}: ${selectedOption?.textContent || "선택"}`);
        custom.menu.replaceChildren();
        Array.from(select.options).forEach(option => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "custom-select-option";
            item.setAttribute("role", "option");
            item.setAttribute("aria-selected", String(option.selected));
            item.disabled = option.disabled;
            item.textContent = option.textContent;
            item.addEventListener("click", event => {
                event.stopPropagation();
                select.value = option.value;
                select.dispatchEvent(new Event("change"));
                closeCustomSelect(custom.wrapper);
                custom.trigger.focus();
            });
            item.addEventListener("keydown", event => {
                const options = Array.from(custom.menu.querySelectorAll("button:not(:disabled)"));
                const index = options.indexOf(item);
                if (event.key === "ArrowDown") {
                    event.preventDefault();
                    options[(index + 1) % options.length]?.focus();
                } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    options[(index - 1 + options.length) % options.length]?.focus();
                } else if (event.key === "Escape") {
                    closeCustomSelect(custom.wrapper);
                    custom.trigger.focus();
                }
            });
            custom.menu.append(item);
        });
    }

    /** 열린 커스텀 드롭다운을 닫고 접근성 상태를 복원한다. */
    function closeCustomSelect(wrapper) {
        wrapper.classList.remove("is-open");
        const trigger = wrapper.querySelector(".custom-select-trigger");
        const menu = wrapper.querySelector(".custom-select-menu");
        trigger?.setAttribute("aria-expanded", "false");
        if (menu) menu.hidden = true;
    }

    /** 0~1 비율을 백분율로 표시하되 작은 위험률의 유효 숫자를 0으로 뭉개지 않는다. */
    function percent(value) {
        if (value == null || !Number.isFinite(Number(value))) return "-";
        const percentage = Number(value) * 100;
        const absolute = Math.abs(percentage);
        if (absolute === 0) return "0.0%";
        if (absolute >= 0.1) return `${percentage.toFixed(1)}%`;
        const precise = percentage.toPrecision(4)
            .replace(/(\.\d*?[1-9])0+$/, "$1")
            .replace(/\.0+$/, "");
        return `${precise}%`;
    }
    /** 금액과 건수를 한국어 숫자 형식으로 표시한다. */
    function number(value) { return value == null ? "-" : Number(value).toLocaleString("ko-KR"); }
    /** UTC로 전달된 실행 시각을 브라우저 설정과 무관하게 한국 시간으로 표시한다. */
    function koreanDateTime(value) {
        if (!value) return "-";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return "-";
        return date.toLocaleString("ko-KR", {timeZone: "Asia/Seoul"});
    }
    /** 오류 문구를 공통 영역과 디자인 모달에 표시한다. */
    function showError(error) {
        const serverError = Number(error?.status) >= 500;
        const message = serverError
            ? "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            : error?.message || "요청 처리에 실패했습니다.";
        const element = document.getElementById("pageError");
        if (element) { element.textContent = message; element.hidden = false; }
        showErrorModal({
            title: serverError ? "서버 오류가 발생했습니다" : "요청을 처리하지 못했습니다",
            message
        });
    }

    /** 모든 화면이 공통으로 사용하는 오류 모달을 생성하고 표시한다. */
    function showErrorModal({title, message}) {
        let modal = document.getElementById("commonErrorModal");
        if (!modal) {
            modal = document.createElement("div");
            modal.id = "commonErrorModal";
            modal.className = "error-modal";
            modal.hidden = true;
            modal.setAttribute("role", "alertdialog");
            modal.setAttribute("aria-modal", "true");
            modal.setAttribute("aria-labelledby", "commonErrorTitle");
            modal.innerHTML = '<div class="error-modal-dialog"><span class="error-modal-icon" aria-hidden="true">!</span><h2 id="commonErrorTitle"></h2><p id="commonErrorMessage"></p><button type="button" class="primary" id="commonErrorClose">확인</button></div>';
            document.body.appendChild(modal);
            modal.querySelector("#commonErrorClose").addEventListener("click", closeErrorModal);
            modal.addEventListener("click", event => { if (event.target === modal) closeErrorModal(); });
            document.addEventListener("keydown", event => { if (event.key === "Escape" && !modal.hidden) closeErrorModal(); });
        }
        modal.querySelector("#commonErrorTitle").textContent = title;
        modal.querySelector("#commonErrorMessage").textContent = message;
        modal.hidden = false;
        document.body.classList.add("has-modal");
        modal.querySelector("#commonErrorClose").focus();
    }

    /** 공통 오류 모달을 닫고 화면 조작을 복구한다. */
    function closeErrorModal() {
        const modal = document.getElementById("commonErrorModal");
        if (!modal) return;
        modal.hidden = true;
        document.body.classList.remove("has-modal");
    }
    /** 화면에 삽입할 문자열의 HTML 특수문자를 치환한다. */
    function escape(value) { const element = document.createElement("span"); element.textContent = value == null ? "" : String(value); return element.innerHTML; }
    /** 모델 피처 키의 화면용 이름과 단위 정보를 반환한다. */
    function modelFeatureMeta(key) { return MODEL_FEATURE_META[key]; }
    function modelFeatureLabel(key, fallback = key) { return MODEL_FEATURE_META[key]?.label || fallback || "-"; }
    return {request, loadBaseMonths, enhanceSelects, percent, number, koreanDateTime, showError, escape, modelFeatureMeta, modelFeatureLabel};
})();
