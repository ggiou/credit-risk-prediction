/** 숨겨진 관리자 화면의 인증, 고객 선택, 다건 AI 분석 진행 상태를 관리한다. */
(() => {
    const selectedCustomers = new Map();
    let currentPage = 0;
    let totalPages = 0;
    let currentItems = [];
    let activeBatchId = null;
    let pollTimer = null;
    let bulkSearch;

    document.addEventListener("DOMContentLoaded", initialize);

    async function initialize() {
        bindEvents();
        bulkSearch = BOBulkCustomerSearch.initialize({
            triggerId: "batchBulkSearchTrigger",
            singleInputId: "batchCustomerQuery",
            formId: "batchSearchForm",
            onBeforeSearch: () => { currentPage = 0; }
        });
        try {
            const session = await BO.request("/api/v1/admin/session");
            if (session.authenticated) await showDashboard();
            else showLogin(session.configured);
        } catch (error) {
            showLogin(true);
            showLoginError(error.message);
        }
    }

    function bindEvents() {
        document.getElementById("adminLoginForm").addEventListener("submit", login);
        document.getElementById("adminLogout").addEventListener("click", logout);
        document.getElementById("batchSearchForm").addEventListener("submit", event => {
            event.preventDefault();
            currentPage = 0;
            loadCustomers().catch(BO.showError);
        });
        document.getElementById("batchPrevPage").addEventListener("click", () => changePage(-1));
        document.getElementById("batchNextPage").addEventListener("click", () => changePage(1));
        document.getElementById("selectPage").addEventListener("change", toggleCurrentPage);
        document.getElementById("startBatch").addEventListener("click", startBatch);
        document.getElementById("retryFailed").addEventListener("click", retryFailed);
    }

    async function login(event) {
        event.preventDefault();
        const button = event.currentTarget.querySelector("button[type=submit]");
        button.disabled = true;
        hideLoginError();
        try {
            await BO.request("/api/v1/admin/session", {
                method: "POST",
                body: JSON.stringify({
                    email: document.getElementById("adminEmail").value.trim(),
                    password: document.getElementById("adminPassword").value
                })
            });
            document.getElementById("adminPassword").value = "";
            await showDashboard();
        } catch (error) {
            showLoginError(error.message);
        } finally {
            button.disabled = false;
        }
    }

    async function logout() {
        clearPolling();
        await BO.request("/api/v1/admin/session", {method: "DELETE"});
        selectedCustomers.clear();
        activeBatchId = null;
        showLogin(true);
    }

    function showLogin(configured) {
        document.getElementById("batchDashboard").hidden = true;
        document.getElementById("adminLoginView").hidden = false;
        if (!configured) showLoginError("관리자 계정이 설정되지 않았습니다. 서버 비공개 설정을 확인해 주세요.");
        setTimeout(() => document.getElementById("adminEmail").focus(), 0);
    }

    async function showDashboard() {
        document.getElementById("adminLoginView").hidden = true;
        document.getElementById("batchDashboard").hidden = false;
        await BO.loadBaseMonths(document.getElementById("baseYmSelect"));
        BO.enhanceSelects();
        await loadCustomers();
    }

    function showLoginError(message) {
        const error = document.getElementById("loginError");
        error.textContent = message;
        error.hidden = false;
    }

    function hideLoginError() {
        document.getElementById("loginError").hidden = true;
    }

    async function changePage(offset) {
        const next = currentPage + offset;
        if (next < 0 || next >= totalPages) return;
        currentPage = next;
        await loadCustomers();
    }

    async function loadCustomers() {
        const hasBulkSearch = bulkSearch?.count() > 0;
        const params = new URLSearchParams({
            baseYm: document.getElementById("baseYmSelect").value,
            page: String(currentPage),
            size: hasBulkSearch ? "50" : "20",
            sort: "customerId,asc",
            analysisOrder: "ACTION_REQUIRED_FIRST"
        });
        const query = document.getElementById("batchCustomerQuery").value.trim();
        const grade = document.getElementById("batchRiskGrade").value;
        const status = document.getElementById("batchAnalysisStatus").value;
        if (!bulkSearch?.appendTo(params) && query) params.set("customerId", query);
        if (grade) params.set("riskGrade", grade);
        if (status) params.set("analysisStatus", status);
        const data = await BO.request(`/api/v1/customers?${params}`);
        currentItems = data.items || [];
        totalPages = data.totalPages || 0;
        renderCustomers();
        document.getElementById("batchPageInfo").textContent = `${totalPages ? currentPage + 1 : 0} / ${totalPages}`;
        document.getElementById("batchPrevPage").disabled = currentPage <= 0;
        document.getElementById("batchNextPage").disabled = currentPage + 1 >= totalPages;
    }

    function renderCustomers() {
        const tbody = document.getElementById("batchCustomerTable");
        tbody.innerHTML = currentItems.map(item => {
            const checked = selectedCustomers.has(item.customerId) ? " checked" : "";
            const analysisUrl = customerAnalysisUrl(item.customerId, item.baseYm);
            return `<tr><td><input class="batch-customer-check" type="checkbox" data-customer-id="${BO.escape(item.customerId)}"${checked} aria-label="${BO.escape(item.customerId)} 선택"></td><td><a class="batch-customer-link" href="${BO.escape(analysisUrl)}" target="_blank" rel="noopener">${BO.escape(item.customerId)}</a></td><td>${BO.escape(item.displayName || "-")}</td><td>${BO.escape(item.baseYm)}</td><td>${BO.escape(analysisStatusName(item.analysisStatus))}</td><td><span class="badge">${BO.escape(item.riskGradeName || "-")}</span></td><td>${BO.percent(item.hazard1m)}</td><td>${BO.percent(item.hazard2m)}</td><td>${BO.percent(item.hazard3m)}</td></tr>`;
        }).join("") || '<tr><td colspan="9">조회 결과가 없습니다.</td></tr>';
        tbody.querySelectorAll(".batch-customer-check").forEach(checkbox => {
            checkbox.addEventListener("change", event => toggleCustomer(event.currentTarget));
        });
        syncSelectionUi();
    }

    function toggleCustomer(checkbox) {
        const item = currentItems.find(candidate => candidate.customerId === checkbox.dataset.customerId);
        if (!item) return;
        if (checkbox.checked && selectedCustomers.size >= 50) {
            checkbox.checked = false;
            BO.showError(new Error("한 번에 최대 50명까지 선택할 수 있습니다."));
            return;
        }
        if (checkbox.checked) selectedCustomers.set(item.customerId, item);
        else selectedCustomers.delete(item.customerId);
        syncSelectionUi();
    }

    function toggleCurrentPage(event) {
        const shouldSelect = event.currentTarget.checked;
        if (shouldSelect && selectedCustomers.size + currentItems.filter(item => !selectedCustomers.has(item.customerId)).length > 50) {
            event.currentTarget.checked = false;
            BO.showError(new Error("현재 페이지를 모두 선택하면 최대 50명을 초과합니다."));
            return;
        }
        currentItems.forEach(item => shouldSelect ? selectedCustomers.set(item.customerId, item) : selectedCustomers.delete(item.customerId));
        renderCustomers();
    }

    function syncSelectionUi() {
        const selectedOnPage = currentItems.filter(item => selectedCustomers.has(item.customerId)).length;
        const selectPage = document.getElementById("selectPage");
        selectPage.checked = currentItems.length > 0 && selectedOnPage === currentItems.length;
        selectPage.indeterminate = selectedOnPage > 0 && selectedOnPage < currentItems.length;
        document.getElementById("selectedCount").textContent = `${selectedCustomers.size}명 선택`;
        const startButton = document.getElementById("startBatch");
        const selectedItems = Array.from(selectedCustomers.values());
        startButton.textContent = selectedItems.length > 0
            && selectedItems.every(item => item.analysisStatus === "OUTDATED")
            ? "선택 고객 다시 분석"
            : "선택 고객 AI 분석";
        startButton.disabled = selectedCustomers.size === 0 || activeBatchId !== null;
    }

    async function startBatch() {
        const button = document.getElementById("startBatch");
        button.disabled = true;
        try {
            const batch = await BO.request("/api/v1/admin/prediction-batches", {
                method: "POST",
                body: JSON.stringify({
                    baseYm: document.getElementById("baseYmSelect").value,
                    customerIds: Array.from(selectedCustomers.keys()),
                    generateExplanation: true
                })
            });
            activeBatchId = batch.batchId;
            document.getElementById("batchProgressPanel").hidden = false;
            renderBatch(batch);
            schedulePoll();
            document.getElementById("batchProgressPanel").scrollIntoView({behavior: "smooth", block: "start"});
        } catch (error) {
            if (error.status === 401) return showLogin(true);
            BO.showError(error);
            button.disabled = false;
        }
    }

    function schedulePoll() {
        clearPolling();
        pollTimer = window.setTimeout(pollBatch, 1500);
    }

    async function pollBatch() {
        if (!activeBatchId) return;
        try {
            const batch = await BO.request(`/api/v1/admin/prediction-batches/${activeBatchId}`);
            renderBatch(batch);
            if (["QUEUED", "RUNNING"].includes(batch.status)) schedulePoll();
            else finishPolling();
        } catch (error) {
            clearPolling();
            if (error.status === 401) return showLogin(true);
            BO.showError(error);
        }
    }

    function renderBatch(batch) {
        document.getElementById("batchProgressPanel").dataset.batchId = String(batch.batchId);
        const finished = batch.completedCount + batch.failedCount;
        const percentage = batch.totalCount ? Math.round(finished / batch.totalCount * 100) : 0;
        document.getElementById("batchProgressBar").style.width = `${percentage}%`;
        document.getElementById("batchStatusText").textContent = batchStatusText(batch.status, percentage);
        document.getElementById("batchTotal").textContent = BO.number(batch.totalCount);
        document.getElementById("batchCompleted").textContent = BO.number(batch.completedCount);
        document.getElementById("batchReused").textContent = BO.number(batch.reusedCount);
        document.getElementById("batchFailed").textContent = BO.number(batch.failedCount);
        document.getElementById("batchPending").textContent = BO.number(batch.pendingCount);
        const failures = (batch.items || []).filter(item => item.status === "FAILED");
        const failureBox = document.getElementById("batchFailures");
        failureBox.hidden = failures.length === 0;
        document.getElementById("batchFailureList").innerHTML = failures.map(item => `<li><strong><a class="batch-customer-link" href="${BO.escape(customerAnalysisUrl(item.customerId, batch.baseYm))}" target="_blank" rel="noopener">${BO.escape(item.customerId)}</a></strong><span>${BO.escape(item.errorMessage || "분석 처리에 실패했습니다.")}</span></li>`).join("");
        document.getElementById("retryFailed").hidden = failures.length === 0 || !["PARTIAL", "FAILED"].includes(batch.status);
    }

    function finishPolling() {
        clearPolling();
        activeBatchId = null;
        syncSelectionUi();
        loadCustomers().catch(BO.showError);
    }

    async function retryFailed() {
        const batchId = activeBatchId || Number(document.getElementById("batchProgressPanel").dataset.batchId);
        if (!batchId) return;
        const button = document.getElementById("retryFailed");
        button.disabled = true;
        try {
            const batch = await BO.request(`/api/v1/admin/prediction-batches/${batchId}/retry-failed`, {method: "POST"});
            activeBatchId = batch.batchId;
            renderBatch(batch);
            schedulePoll();
        } catch (error) {
            BO.showError(error);
        } finally {
            button.disabled = false;
        }
    }

    function clearPolling() {
        if (pollTimer) window.clearTimeout(pollTimer);
        pollTimer = null;
    }

    function batchStatusText(status, percentage) {
        return {QUEUED: "분석 작업을 준비하고 있습니다.", RUNNING: `고객별 분석을 진행하고 있습니다. ${percentage}%`, COMPLETED: "모든 고객의 분석이 완료되었습니다.", PARTIAL: "일부 고객의 분석이 완료되지 않았습니다.", FAILED: "분석이 완료되지 않았습니다."}[status] || status;
    }

    function analysisStatusName(status) {
        return {NOT_ANALYZED: "미분석", OUTDATED: "재분석 필요", COMPLETED: "완료", PARTIAL: "부분 완료"}[status] || status || "-";
    }

    function customerAnalysisUrl(customerId, baseYm) {
        return `/customers/${encodeURIComponent(customerId)}/ai-analysis?baseYm=${encodeURIComponent(baseYm || "")}`;
    }

})();
