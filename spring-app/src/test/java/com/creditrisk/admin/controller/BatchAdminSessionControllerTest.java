package com.creditrisk.admin.controller;

import com.creditrisk.admin.service.BatchAdminAccessService;
import com.creditrisk.common.exception.GlobalExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class BatchAdminSessionControllerTest {

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        BatchAdminAccessService accessService = new BatchAdminAccessService(
                "admin@miribom.test", "safe-password");
        mockMvc = MockMvcBuilders.standaloneSetup(new BatchAdminSessionController(accessService))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void createsAdminSessionForValidSecretCredentials() throws Exception {
        mockMvc.perform(post("/api/v1/admin/session")
                        .contentType("application/json")
                        .content("{\"email\":\"admin@miribom.test\",\"password\":\"safe-password\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.authenticated").value(true))
                .andExpect(jsonPath("$.data.email").value("admin@miribom.test"));
    }

    @Test
    void rejectsInvalidCredentials() throws Exception {
        mockMvc.perform(post("/api/v1/admin/session")
                        .contentType("application/json")
                        .content("{\"email\":\"admin@miribom.test\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("ADMIN_LOGIN_FAILED"));
    }
}
