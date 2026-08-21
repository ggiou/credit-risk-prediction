<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<aside class="sidebar">
    <div class="brand"><span class="brand-mark">M</span><div><strong>미리봄</strong><small>Credit Risk BO</small></div></div>
    <nav>
        <a class="nav-item ${menu eq 'dashboard' ? 'active' : ''}" href="${pageContext.request.contextPath}/">대시보드</a>
        <p class="nav-group">고객 관리</p>
        <a class="nav-item ${menu eq 'customers' ? 'active' : ''}" href="${pageContext.request.contextPath}/customers">고객 목록</a>
        <p class="nav-group">예측 관리</p>
        <a class="nav-item ${menu eq 'predictions' ? 'active' : ''}" href="${pageContext.request.contextPath}/predictions">예측 이력</a>
    </nav>
</aside>

