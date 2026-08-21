/** 공통 API 호출과 화면 표시 유틸리티를 제공한다. */
const BO = (() => {
    /** JSON API를 호출하고 공통 오류 응답을 예외로 변환한다. */
    async function request(path, options = {}) {
        const response = await fetch(path, {headers: {"Accept": "application/json", "Content-Type": "application/json", ...(options.headers || {})}, ...options});
        const body = await response.json().catch(() => ({}));
        if (!response.ok || body.success === false) {
            // 서버 오류의 안전한 사용자 메시지만 화면 코드로 전달한다.
            const error = new Error(body.error?.message || body.detail?.message || "요청 처리에 실패했습니다.");
            error.code = body.error?.code; error.status = response.status; throw error;
        }
        return body.data ?? body;
    }

    /** 기준년월 선택 상자를 실제 적재월로 채운다. */
    async function loadBaseMonths(select, includeAll = false) {
        if (!select) return null;
        const data = await request("/api/v1/meta/base-months");
        const selected = new URLSearchParams(location.search).get("baseYm") || data.defaultBaseYm;
        select.innerHTML = includeAll ? '<option value="">전체</option>' : "";
        data.baseMonths.forEach(month => select.add(new Option(month, month, false, month === selected)));
        return selected;
    }

    /** 0~1 위험률을 소수점 한 자리 백분율로 표시한다. */
    function percent(value) { return value == null ? "-" : `${(Number(value) * 100).toFixed(1)}%`; }
    /** 금액과 건수를 한국어 숫자 형식으로 표시한다. */
    function number(value) { return value == null ? "-" : Number(value).toLocaleString("ko-KR"); }
    /** 오류 문구를 공통 영역에 표시한다. */
    function showError(error) { const element = document.getElementById("pageError"); if (element) { element.textContent = error.message; element.hidden = false; } }
    /** 화면에 삽입할 문자열의 HTML 특수문자를 치환한다. */
    function escape(value) { const element = document.createElement("span"); element.textContent = value == null ? "" : String(value); return element.innerHTML; }
    return {request, loadBaseMonths, percent, number, showError, escape};
})();

