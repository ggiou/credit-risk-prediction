package com.creditrisk.prediction.service;

import com.creditrisk.prediction.dto.PredictionExecutionResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class PredictionBatchWorkerTest {

    @Mock private PredictionBatchService batchService;
    @Mock private PredictionCommandService commandService;
    private PredictionBatchWorker worker;

    @BeforeEach
    void setUp() {
        worker = new PredictionBatchWorker(batchService, commandService, Runnable::run);
        when(batchService.start(10L)).thenReturn(new PredictionBatchService.BatchWork(
                "201812", true, List.of(new PredictionBatchService.WorkItem(20L, "SYN_1"))));
        when(batchService.markItemRunning(10L, 20L)).thenReturn(true);
    }

    @Test
    void recordsReusedPredictionAsSuccessfulItem() {
        when(commandService.execute("SYN_1", "201812", true, "batch-10-item-20"))
                .thenReturn(result(true, "COMPLETED"));

        worker.process(10L);

        verify(batchService).markItemSucceeded(10L, 20L, 99L, true);
        verify(batchService).finish(10L);
    }

    @Test
    void keepsLightGbmPredictionAndMarksItemFailedWhenLlmIsPartial() {
        when(commandService.execute("SYN_1", "201812", true, "batch-10-item-20"))
                .thenReturn(result(false, "PARTIAL"));

        worker.process(10L);

        verify(batchService).markItemFailed(
                10L, 20L, 99L, "LLM_EXPLANATION_FAILED",
                "LightGBM 예측은 저장됐지만 LLM 설명 생성에 실패했습니다.");
        verify(batchService).finish(10L);
    }

    private PredictionExecutionResponse result(boolean reused, String analysisStatus) {
        return new PredictionExecutionResponse(
                99L, "SYN_1", "201812", reused, analysisStatus,
                "miribom-lgbm-v0.3", "v1", null, List.of(), null, null,
                null, null, null);
    }
}
