<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html>
<html lang="ko">
<head>
    <jsp:include page="../common/head.jsp"/>
</head>
<body class="error-page">
<main class="error-page-card">
    <div class="error-page-code">500</div>
    <h1>서비스 처리 중 오류가 발생했습니다.</h1>
    <p>잠시 후 다시 시도해 주세요.<br>문제가 계속되면 관리자에게 문의해 주세요.</p>
    <a class="primary" href="${pageContext.request.contextPath}/">대시보드로 이동</a>
</main>
</body>
</html>
