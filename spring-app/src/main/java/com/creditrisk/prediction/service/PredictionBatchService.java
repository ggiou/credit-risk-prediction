package com.creditrisk.prediction.service;

import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.customer.service.CustomerDetailService;
import com.creditrisk.prediction.dto.PredictionBatchCreateRequest;
import com.creditrisk.prediction.dto.PredictionBatchResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.atomic.AtomicLong;

/** DB 스키마를 확장하지 않고 현재 서버 프로세스에서 다건 분석 진행 상태를 관리한다. */
@Service
public class PredictionBatchService {

    private static final int MAX_RETAINED_BATCHES = 100;

    private final CustomerDetailService customerDetailService;
    private final int maxCustomers;
    private final AtomicLong batchSequence = new AtomicLong();
    private final AtomicLong itemSequence = new AtomicLong();
    private final ConcurrentMap<Long, BatchState> batches = new ConcurrentHashMap<>();
    private final Object reservationMonitor = new Object();
    private final Map<String, Long> activeCustomerRuns = new HashMap<>();

    public PredictionBatchService(
            CustomerDetailService customerDetailService,
            @Value("${admin.batch.max-customers:50}") int maxCustomers) {
        this.customerDetailService = customerDetailService;
        this.maxCustomers = Math.max(1, Math.min(50, maxCustomers));
    }

    public long create(PredictionBatchCreateRequest request, String requestedBy) {
        List<String> customerIds = request.customerIds().stream().distinct().toList();
        if (customerIds.size() > maxCustomers) {
            throw new BusinessException("BATCH_SIZE_EXCEEDED", "한 번에 최대 " + maxCustomers + "명까지 분석할 수 있습니다.",
                    HttpStatus.BAD_REQUEST, Map.of("maxCustomers", maxCustomers));
        }
        customerIds.forEach(customerDetailService::validateCustomer);
        long batchId = batchSequence.incrementAndGet();
        synchronized (reservationMonitor) {
            List<String> conflicts = customerIds.stream()
                    .filter(customerId -> activeCustomerRuns.containsKey(runKey(customerId, request.baseYm())))
                    .toList();
            if (!conflicts.isEmpty()) {
                throw new BusinessException(
                        "BATCH_CUSTOMERS_ALREADY_RUNNING",
                        "이미 분석 중인 고객이 포함되어 있습니다. 진행 중인 작업이 끝난 뒤 다시 시도해 주세요.",
                        HttpStatus.CONFLICT,
                        Map.of("customerIds", conflicts, "baseYm", request.baseYm()));
            }
            customerIds.forEach(customerId -> activeCustomerRuns.put(runKey(customerId, request.baseYm()), batchId));
            try {
                pruneCompletedBatches();
                LinkedHashMap<Long, ItemState> items = new LinkedHashMap<>();
                customerIds.forEach(customerId -> {
                    long itemId = itemSequence.incrementAndGet();
                    items.put(itemId, new ItemState(itemId, customerId));
                });
                batches.put(batchId, new BatchState(
                        batchId, requestedBy, request.baseYm(), request.shouldGenerateExplanation(), Instant.now(), items));
                return batchId;
            } catch (RuntimeException exception) {
                customerIds.forEach(customerId -> activeCustomerRuns.remove(runKey(customerId, request.baseYm()), batchId));
                throw exception;
            }
        }
    }

    public PredictionBatchResponse get(long batchId) {
        BatchState batch = requireBatch(batchId);
        synchronized (batch) {
            return toResponse(batch);
        }
    }

    public void retryFailed(long batchId) {
        BatchState batch = requireBatch(batchId);
        synchronized (batch) {
            List<ItemState> failedItems = batch.items.values().stream()
                    .filter(item -> "FAILED".equals(item.status))
                    .toList();
            if (failedItems.isEmpty() || !("PARTIAL".equals(batch.status) || "FAILED".equals(batch.status))) {
                throw new BusinessException("NO_FAILED_BATCH_ITEMS", "재시도할 실패 고객이 없습니다.",
                        HttpStatus.CONFLICT, Map.of("batchId", batchId));
            }
            synchronized (reservationMonitor) {
                List<String> conflicts = failedItems.stream()
                        .map(item -> item.customerId)
                        .filter(customerId -> activeCustomerRuns.containsKey(runKey(customerId, batch.baseYm)))
                        .toList();
                if (!conflicts.isEmpty()) {
                    throw new BusinessException(
                            "BATCH_CUSTOMERS_ALREADY_RUNNING",
                            "이미 분석 중인 고객은 재시도할 수 없습니다.",
                            HttpStatus.CONFLICT,
                            Map.of("customerIds", conflicts, "baseYm", batch.baseYm));
                }
                failedItems.forEach(item -> activeCustomerRuns.put(runKey(item.customerId, batch.baseYm), batch.batchId));
                failedItems.forEach(item -> {
                    item.status = "PENDING";
                    item.predictionId = null;
                    item.errorCode = null;
                    item.errorMessage = null;
                });
                batch.status = "QUEUED";
                batch.completedAt = null;
            }
        }
    }

    BatchWork start(long batchId) {
        BatchState batch = requireBatch(batchId);
        synchronized (batch) {
            if (!"QUEUED".equals(batch.status)) return null;
            batch.status = "RUNNING";
            if (batch.startedAt == null) batch.startedAt = Instant.now();
            List<WorkItem> items = batch.items.values().stream()
                    .filter(item -> "PENDING".equals(item.status))
                    .map(item -> new WorkItem(item.batchItemId, item.customerId))
                    .toList();
            return new BatchWork(batch.baseYm, batch.generateExplanation, items);
        }
    }

    boolean markItemRunning(long batchId, long batchItemId) {
        BatchState batch = requireBatch(batchId);
        synchronized (batch) {
            ItemState item = batch.items.get(batchItemId);
            if (item == null || !"PENDING".equals(item.status)) return false;
            item.status = "RUNNING";
            item.errorCode = null;
            item.errorMessage = null;
            return true;
        }
    }

    void markItemSucceeded(long batchId, long batchItemId, long predictionId, boolean reused) {
        updateItem(batchId, batchItemId, reused ? "REUSED" : "COMPLETED", predictionId, null, null);
    }

    void markItemFailed(long batchId, long batchItemId, Long predictionId, String errorCode, String errorMessage) {
        updateItem(batchId, batchItemId, "FAILED", predictionId, errorCode, errorMessage);
    }

    void finish(long batchId) {
        BatchState batch = requireBatch(batchId);
        synchronized (batch) {
            long failed = batch.items.values().stream().filter(item -> "FAILED".equals(item.status)).count();
            batch.status = failed == 0 ? "COMPLETED" : failed == batch.items.size() ? "FAILED" : "PARTIAL";
            batch.completedAt = Instant.now();
            synchronized (reservationMonitor) {
                batch.items.values().forEach(item ->
                        activeCustomerRuns.remove(runKey(item.customerId, batch.baseYm), batch.batchId));
            }
        }
    }

    private void updateItem(
            long batchId,
            long batchItemId,
            String status,
            Long predictionId,
            String errorCode,
            String errorMessage) {
        BatchState batch = requireBatch(batchId);
        synchronized (batch) {
            ItemState item = batch.items.get(batchItemId);
            if (item == null) return;
            item.status = status;
            item.predictionId = predictionId;
            item.errorCode = errorCode;
            item.errorMessage = errorMessage;
            if ("COMPLETED".equals(status) || "REUSED".equals(status) || "FAILED".equals(status)) {
                synchronized (reservationMonitor) {
                    activeCustomerRuns.remove(runKey(item.customerId, batch.baseYm), batch.batchId);
                }
            }
        }
    }

    private PredictionBatchResponse toResponse(BatchState batch) {
        List<PredictionBatchResponse.Item> items = batch.items.values().stream()
                .map(item -> new PredictionBatchResponse.Item(
                        item.batchItemId, item.customerId, item.status, item.predictionId,
                        item.errorCode, item.errorMessage))
                .toList();
        int completed = (int) batch.items.values().stream()
                .filter(item -> "COMPLETED".equals(item.status) || "REUSED".equals(item.status)).count();
        int reused = (int) batch.items.values().stream().filter(item -> "REUSED".equals(item.status)).count();
        int failed = (int) batch.items.values().stream().filter(item -> "FAILED".equals(item.status)).count();
        int total = batch.items.size();
        return new PredictionBatchResponse(
                batch.batchId, batch.requestedBy, batch.baseYm, batch.generateExplanation, batch.status,
                total, completed, reused, failed, Math.max(0, total - completed - failed),
                batch.createdAt, batch.startedAt, batch.completedAt, items);
    }

    private BatchState requireBatch(long batchId) {
        BatchState batch = batches.get(batchId);
        if (batch == null) {
            throw new BusinessException("PREDICTION_BATCH_NOT_FOUND", "다건 분석 작업을 찾을 수 없습니다.",
                    HttpStatus.NOT_FOUND, Map.of("batchId", batchId));
        }
        return batch;
    }

    private void pruneCompletedBatches() {
        if (batches.size() < MAX_RETAINED_BATCHES) return;
        int removeCount = Math.max(1, batches.size() - MAX_RETAINED_BATCHES + 1);
        batches.entrySet().stream()
                .filter(entry -> List.of("COMPLETED", "PARTIAL", "FAILED").contains(entry.getValue().status))
                .sorted(Map.Entry.comparingByKey())
                .limit(removeCount)
                .map(Map.Entry::getKey)
                .toList()
                .forEach(batches::remove);
    }

    private String runKey(String customerId, String baseYm) {
        return customerId + "\u0000" + baseYm;
    }

    record BatchWork(String baseYm, boolean generateExplanation, List<WorkItem> items) {}
    record WorkItem(long batchItemId, String customerId) {}

    private static final class BatchState {
        private final long batchId;
        private final String requestedBy;
        private final String baseYm;
        private final boolean generateExplanation;
        private final Instant createdAt;
        private final LinkedHashMap<Long, ItemState> items;
        private String status = "QUEUED";
        private Instant startedAt;
        private Instant completedAt;

        private BatchState(long batchId, String requestedBy, String baseYm, boolean generateExplanation,
                           Instant createdAt, LinkedHashMap<Long, ItemState> items) {
            this.batchId = batchId;
            this.requestedBy = requestedBy;
            this.baseYm = baseYm;
            this.generateExplanation = generateExplanation;
            this.createdAt = createdAt;
            this.items = items;
        }
    }

    private static final class ItemState {
        private final long batchItemId;
        private final String customerId;
        private String status = "PENDING";
        private Long predictionId;
        private String errorCode;
        private String errorMessage;

        private ItemState(long batchItemId, String customerId) {
            this.batchItemId = batchItemId;
            this.customerId = customerId;
        }
    }
}
