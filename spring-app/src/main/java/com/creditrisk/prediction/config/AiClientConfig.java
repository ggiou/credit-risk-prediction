package com.creditrisk.prediction.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

/**
 * 내부 FastAPI 호출용 HTTP 클라이언트와 타임아웃을 구성한다.
 */
@Configuration
public class AiClientConfig {

    /**
     * AI 서버 기본 주소와 연결·읽기 타임아웃이 적용된 RestClient를 생성한다.
     */
    @Bean
    public RestClient aiRestClient(
            @Value("${ai.server.base-url}") String baseUrl,
            @Value("${ai.server.connect-timeout-seconds}") long connectTimeoutSeconds,
            @Value("${ai.server.read-timeout-seconds:0}") long readTimeoutSeconds) {
        // 외부 AI 서버 장애가 Spring 요청 스레드를 무기한 점유하지 않도록 두 타임아웃을 모두 설정한다.
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(connectTimeoutSeconds));
        requestFactory.setReadTimeout(Duration.ofSeconds(readTimeoutSeconds));
        return RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(requestFactory)
                .build();
    }
}

