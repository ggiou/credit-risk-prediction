/** 고객번호 또는 고객명을 최대 50개까지 다량 검색하는 공통 모달을 제공한다. */
const BOBulkCustomerSearch = (() => {
    const MAX_VALUES = 50;

    function initialize({triggerId, singleInputId, formId, onBeforeSearch}) {
        const modal = document.getElementById("bulkCustomerSearchModal");
        const trigger = document.getElementById(triggerId);
        const singleInput = document.getElementById(singleInputId);
        const form = document.getElementById(formId);
        const textarea = document.getElementById("bulkCustomerValues");
        const counter = document.getElementById("bulkCustomerValueCount");
        const error = document.getElementById("bulkCustomerSearchError");
        let applied = null;

        const selectedType = () => modal.querySelector('input[name="bulkSearchType"]:checked').value;
        const parseValues = () => Array.from(new Set(textarea.value
            .split(/\r?\n|,/)
            .map(value => value.trim())
            .filter(Boolean)));

        function updateCount() {
            const count = parseValues().length;
            counter.textContent = `${count} / ${MAX_VALUES}개`;
            counter.classList.toggle("is-over-limit", count > MAX_VALUES);
            error.hidden = true;
        }

        function updateTrigger() {
            if (!applied) {
                trigger.classList.remove("is-active");
                trigger.setAttribute("aria-label", "다량 검색");
                trigger.title = "다량 검색";
                singleInput.disabled = false;
                return;
            }
            const typeLabel = applied.type === "customerIds" ? "고객번호" : "고객명";
            trigger.classList.add("is-active");
            trigger.setAttribute("aria-label", `다량 검색: ${typeLabel} ${applied.values.length}개 적용됨`);
            trigger.title = `${typeLabel} ${applied.values.length}개 적용됨`;
            singleInput.disabled = true;
        }

        function close() {
            modal.close();
        }

        function clear(runSearch) {
            applied = null;
            textarea.value = "";
            updateCount();
            updateTrigger();
            close();
            if (runSearch) {
                onBeforeSearch?.();
                form.requestSubmit();
            }
        }

        trigger.addEventListener("click", () => {
            error.hidden = true;
            modal.showModal();
            setTimeout(() => textarea.focus(), 0);
        });
        modal.querySelectorAll('input[name="bulkSearchType"]').forEach(radio => {
            radio.addEventListener("change", () => {
                textarea.placeholder = selectedType() === "customerIds"
                    ? "고객번호를 입력해주세요"
                    : "고객명을 입력해주세요";
                setTimeout(() => textarea.focus(), 0);
            });
        });
        textarea.addEventListener("input", updateCount);
        document.getElementById("closeBulkCustomerSearch").addEventListener("click", close);
        document.getElementById("cancelBulkCustomerSearch").addEventListener("click", close);
        document.getElementById("clearBulkCustomerSearch").addEventListener("click", () => clear(true));
        document.getElementById("applyBulkCustomerSearch").addEventListener("click", () => {
            const values = parseValues();
            if (values.length === 0 || values.length > MAX_VALUES) {
                error.textContent = values.length === 0
                    ? "검색할 고객번호 또는 고객명을 입력해 주세요."
                    : `검색값은 최대 ${MAX_VALUES}개까지 입력할 수 있습니다.`;
                error.hidden = false;
                return;
            }
            applied = {type: selectedType(), values};
            updateTrigger();
            close();
            onBeforeSearch?.();
            form.requestSubmit();
        });
        modal.addEventListener("click", event => {
            if (event.target === modal) close();
        });
        updateCount();
        updateTrigger();

        return {
            appendTo(params) {
                if (!applied) return false;
                applied.values.forEach(value => params.append(applied.type, value));
                return true;
            },
            count() {
                return applied?.values.length || 0;
            }
        };
    }

    return {initialize};
})();
