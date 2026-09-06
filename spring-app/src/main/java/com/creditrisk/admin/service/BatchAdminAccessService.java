package com.creditrisk.admin.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** 비공개 설정의 관리자 자격정보를 로그에 노출하지 않고 검증한다. */
@Service
public class BatchAdminAccessService {

    private final String email;
    private final String password;

    public BatchAdminAccessService(
            @Value("${admin.batch.email:}") String email,
            @Value("${admin.batch.password:}") String password) {
        this.email = email;
        this.password = password;
    }

    public boolean authenticate(String candidateEmail, String candidatePassword) {
        return !email.isBlank() && !password.isBlank()
                && candidateEmail != null && candidatePassword != null
                && secureEquals(email, candidateEmail)
                && secureEquals(password, candidatePassword);
    }

    public boolean configured() {
        return !email.isBlank() && !password.isBlank();
    }

    private boolean secureEquals(String expected, String actual) {
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                actual.getBytes(StandardCharsets.UTF_8));
    }
}
