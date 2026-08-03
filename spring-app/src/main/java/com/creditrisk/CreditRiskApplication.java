package com.creditrisk;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;

/**
 * 신용카드 연체 위험 조기예측 BO 애플리케이션의 시작점이다.
 */
@SpringBootApplication
public class CreditRiskApplication extends SpringBootServletInitializer {

    /**
     * 외부 톰캣에 WAR 파일로 배포할 때 애플리케이션 구성을 등록한다.
     *
     * @param application 외부 톰캣이 전달한 애플리케이션 빌더
     * @return Spring Boot 애플리케이션 빌더
     */
    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        // JSP는 실행형 JAR 제약이 있으므로 WAR 배포도 지원하도록 시작 클래스를 지정한다.
        return application.sources(CreditRiskApplication.class);
    }

    /**
     * 로컬 개발 환경에서 내장 톰캣으로 애플리케이션을 실행한다.
     *
     * @param args 실행 인자
     */
    public static void main(String[] args) {
        // Spring 컨텍스트와 내장 톰캣을 함께 시작한다.
        SpringApplication.run(CreditRiskApplication.class, args);
    }
}

