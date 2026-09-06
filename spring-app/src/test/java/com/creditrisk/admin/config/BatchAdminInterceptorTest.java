package com.creditrisk.admin.config;

import com.creditrisk.admin.controller.BatchAdminSessionController;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

class BatchAdminInterceptorTest {

    private final BatchAdminInterceptor interceptor = new BatchAdminInterceptor();

    @Test
    void rejectsBatchApiWithoutAdminSession() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();

        boolean allowed = interceptor.preHandle(new MockHttpServletRequest(), response, new Object());

        assertThat(allowed).isFalse();
        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).contains("ADMIN_LOGIN_REQUIRED");
    }

    @Test
    void allowsBatchApiWithAdminSession() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.getSession().setAttribute(BatchAdminSessionController.SESSION_EMAIL, "admin@miribom.test");

        boolean allowed = interceptor.preHandle(request, new MockHttpServletResponse(), new Object());

        assertThat(allowed).isTrue();
    }
}
