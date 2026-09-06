package com.creditrisk.prediction.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

/** 다건 분석의 작업 조율과 AI 호출 동시성을 분리한다. */
@Configuration
@EnableAsync
public class PredictionBatchConfig {

    @Bean("predictionBatchCoordinatorExecutor")
    Executor coordinatorExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(1);
        executor.setMaxPoolSize(1);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("prediction-batch-");
        executor.initialize();
        return executor;
    }

    @Bean("predictionBatchItemExecutor")
    Executor itemExecutor(@Value("${admin.batch.concurrency:2}") int configuredConcurrency) {
        int concurrency = Math.max(1, Math.min(3, configuredConcurrency));
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(concurrency);
        executor.setMaxPoolSize(concurrency);
        executor.setQueueCapacity(200);
        executor.setThreadNamePrefix("prediction-item-");
        executor.initialize();
        return executor;
    }
}
