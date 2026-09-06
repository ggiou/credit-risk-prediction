package com.creditrisk.admin.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class BatchAdminAccessServiceTest {

    @Test
    void authenticatesOnlyConfiguredExactCredentials() {
        BatchAdminAccessService service = new BatchAdminAccessService("admin@miribom.test", "safe-password");

        assertThat(service.configured()).isTrue();
        assertThat(service.authenticate("admin@miribom.test", "safe-password")).isTrue();
        assertThat(service.authenticate("ADMIN@miribom.test", "safe-password")).isFalse();
        assertThat(service.authenticate("admin@miribom.test", "wrong-password")).isFalse();
    }

    @Test
    void rejectsAuthenticationWhenSecretIsNotConfigured() {
        BatchAdminAccessService service = new BatchAdminAccessService("", "");

        assertThat(service.configured()).isFalse();
        assertThat(service.authenticate("admin@miribom.test", "safe-password")).isFalse();
    }
}
