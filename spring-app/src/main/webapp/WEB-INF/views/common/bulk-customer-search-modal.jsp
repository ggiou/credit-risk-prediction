<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<dialog id="bulkCustomerSearchModal" class="bulk-search-modal" aria-labelledby="bulkSearchTitle">
    <form method="dialog" class="bulk-search-dialog">
        <div class="bulk-search-title">
            <div><small>다량 고객 검색</small><h2 id="bulkSearchTitle">여러 고객을 한 번에 조회</h2></div>
            <button id="closeBulkCustomerSearch" class="bulk-search-close" type="button" aria-label="닫기">×</button>
        </div>
        <fieldset class="bulk-search-type">
            <legend>검색 기준</legend>
            <label><input type="radio" name="bulkSearchType" value="customerIds" checked> 고객번호</label>
            <label><input type="radio" name="bulkSearchType" value="customerNames"> 고객명</label>
        </fieldset>
        <label class="bulk-search-input-label" for="bulkCustomerValues">검색값</label>
        <textarea id="bulkCustomerValues" rows="9" placeholder="SYN_100&#10;SYN_1004&#10;SYN_2030"></textarea>
        <div class="bulk-search-help">
            <span>한 줄에 하나씩 입력하세요. 쉼표로 구분해도 됩니다.</span>
            <strong id="bulkCustomerValueCount">0 / 50개</strong>
        </div>
        <p id="bulkCustomerSearchError" class="error-message" hidden></p>
        <div class="bulk-search-actions">
            <button id="clearBulkCustomerSearch" class="secondary" type="button">다량 검색 해제</button>
            <button id="cancelBulkCustomerSearch" type="button">취소</button>
            <button id="applyBulkCustomerSearch" class="primary" type="button">적용하고 조회</button>
        </div>
    </form>
</dialog>
