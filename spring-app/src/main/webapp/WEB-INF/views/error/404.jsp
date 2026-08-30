<%@ page contentType="text/html; charset=UTF-8" pageEncoding="UTF-8" %>
<!DOCTYPE html>
<html lang="ko">
<head>
    <jsp:include page="../common/head.jsp"/>
</head>
<body class="error-page">
<main class="error-page-card">
    <div class="error-page-code">404</div>
    <h1>요청한 페이지를 찾을 수 없습니다.</h1>
    <p>주소가 잘못 입력되었거나 페이지가 이동되었을 수 있습니다.<br>주소를 확인한 뒤 다시 시도해 주세요.</p>
    <a class="primary" href="${pageContext.request.contextPath}/">대시보드로 이동</a>
</main>
</body>
</html>
