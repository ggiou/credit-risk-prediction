package com.creditrisk.prediction.controller;

import com.creditrisk.admin.controller.BatchAdminSessionController;
import com.creditrisk.common.api.ApiResponse;
import com.creditrisk.common.web.RequestIds;
import com.creditrisk.prediction.dto.PredictionBatchCreateRequest;
import com.creditrisk.prediction.dto.PredictionBatchResponse;
import com.creditrisk.prediction.service.PredictionBatchService;
import com.creditrisk.prediction.service.PredictionBatchWorker;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 별도 관리자 화면에서 사용하는 다건 AI 분석 API다. */
@RestController
@RequestMapping("/api/v1/admin/prediction-batches")
public class PredictionBatchController {

    private final PredictionBatchService service;
    private final PredictionBatchWorker worker;

    public PredictionBatchController(PredictionBatchService service, PredictionBatchWorker worker) {
        this.service = service;
        this.worker = worker;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<PredictionBatchResponse>> create(
            @Valid @RequestBody PredictionBatchCreateRequest body,
            HttpServletRequest request) {
        String requestedBy = String.valueOf(request.getSession(false)
                .getAttribute(BatchAdminSessionController.SESSION_EMAIL));
        long batchId = service.create(body, requestedBy);
        worker.process(batchId);
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(ApiResponse.success(service.get(batchId), RequestIds.from(request)));
    }

    @GetMapping("/{batchId}")
    public ApiResponse<PredictionBatchResponse> get(@PathVariable long batchId, HttpServletRequest request) {
        return ApiResponse.success(service.get(batchId), RequestIds.from(request));
    }

    @PostMapping("/{batchId}/retry-failed")
    public ResponseEntity<ApiResponse<PredictionBatchResponse>> retryFailed(
            @PathVariable long batchId,
            HttpServletRequest request) {
        service.retryFailed(batchId);
        worker.process(batchId);
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(ApiResponse.success(service.get(batchId), RequestIds.from(request)));
    }
}
