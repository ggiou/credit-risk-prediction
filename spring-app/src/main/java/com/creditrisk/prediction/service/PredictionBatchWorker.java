package com.creditrisk.prediction.service;

import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.prediction.dto.PredictionExecutionResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

/** 접수된 배치를 제한된 동시성으로 처리하고 고객별 실패를 격리한다. */
@Component
public class PredictionBatchWorker {

    private static final Logger log = LoggerFactory.getLogger(PredictionBatchWorker.class);

    private final PredictionBatchService batchService;
    private final PredictionCommandService commandService;
    private final Executor itemExecutor;

    public PredictionBatchWorker(
            PredictionBatchService batchService,
            PredictionCommandService commandService,
            @Qualifier("predictionBatchItemExecutor") Executor itemExecutor) {
        this.batchService = batchService;
        this.commandService = commandService;
        this.itemExecutor = itemExecutor;
    }

    @Async("predictionBatchCoordinatorExecutor")
    public void process(long batchId) {
        PredictionBatchService.BatchWork batch = batchService.start(batchId);
        if (batch == null) return;
        var futures = batch.items().stream()
                .map(item -> CompletableFuture.runAsync(
                        () -> processItem(batchId, item, batch.baseYm(), batch.generateExplanation()), itemExecutor))
                .toList();
        CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new)).join();
        batchService.finish(batchId);
    }

    private void processItem(
            long batchId,
            PredictionBatchService.WorkItem item,
            String baseYm,
            boolean generateExplanation) {
        long batchItemId = item.batchItemId();
        String customerId = item.customerId();
        if (!batchService.markItemRunning(batchId, batchItemId)) return;
        try {
            PredictionExecutionResponse result = commandService.execute(
                    customerId, baseYm, generateExplanation, "batch-" + batchId + "-item-" + batchItemId);
            if ("PARTIAL".equals(result.analysisStatus())) {
                batchService.markItemFailed(batchId, batchItemId, result.predictionId(), "LLM_EXPLANATION_FAILED",
                        "LightGBM 예측은 저장됐지만 LLM 설명 생성에 실패했습니다.");
            } else {
                batchService.markItemSucceeded(batchId, batchItemId, result.predictionId(), result.reused());
            }
        } catch (Exception exception) {
            String code = exception instanceof BusinessException business ? business.getCode() : "BATCH_ITEM_FAILED";
            String message = exception.getMessage() == null ? "다건 분석 처리에 실패했습니다." : exception.getMessage();
            if (message.length() > 500) message = message.substring(0, 500);
            batchService.markItemFailed(batchId, batchItemId, null, code, message);
            log.error("다건 AI 분석 고객 처리 실패 batchId={} batchItemId={} customerId={} baseYm={} code={}",
                    batchId, batchItemId, customerId, baseYm, code, exception);
        }
    }
}
