package com.creditrisk.admin.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class BatchAdminWebConfig implements WebMvcConfigurer {
    private final BatchAdminInterceptor interceptor;

    public BatchAdminWebConfig(BatchAdminInterceptor interceptor) {
        this.interceptor = interceptor;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(interceptor)
                .addPathPatterns(
                        "/api/v1/admin/prediction-batches",
                        "/api/v1/admin/prediction-batches/**");
    }
}
