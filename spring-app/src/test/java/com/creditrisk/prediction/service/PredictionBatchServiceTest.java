package com.creditrisk.prediction.service;

import com.creditrisk.common.exception.BusinessException;
import com.creditrisk.customer.service.CustomerDetailService;
import com.creditrisk.prediction.dto.PredictionBatchCreateRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class PredictionBatchServiceTest {

    @Mock private CustomerDetailService customerDetailService;
    private PredictionBatchService service;

    @BeforeEach
    void setUp() {
        service = new PredictionBatchService(customerDetailService, 50);
    }

    @Test
    void createsOneItemPerDistinctCustomerAndRecordsAdministrator() {
        PredictionBatchCreateRequest request = new PredictionBatchCreateRequest(
                "201812", List.of("SYN_1", "SYN_1", "SYN_2"), true);

        long batchId = service.create(request, "admin@miribom.test");

        assertThat(service.get(batchId).requestedBy()).isEqualTo("admin@miribom.test");
        assertThat(service.get(batchId).baseYm()).isEqualTo("201812");
        assertThat(service.get(batchId).totalCount()).isEqualTo(2);
        assertThat(service.get(batchId).status()).isEqualTo("QUEUED");
        verify(customerDetailService).validateCustomer("SYN_1");
        verify(customerDetailService).validateCustomer("SYN_2");
    }

    @Test
    void rejectsSameCustomerAndBaseMonthWhileExistingBatchIsRunning() {
        PredictionBatchCreateRequest request = new PredictionBatchCreateRequest(
                "201812", List.of("SYN_1"), true);
        service.create(request, "admin@miribom.test");

        assertThatThrownBy(() -> service.create(request, "admin@miribom.test"))
                .isInstanceOfSatisfying(BusinessException.class, exception -> {
                    assertThat(exception.getCode()).isEqualTo("BATCH_CUSTOMERS_ALREADY_RUNNING");
                    assertThat(exception.getStatus().value()).isEqualTo(409);
                    assertThat(exception.getDetails()).containsEntry("customerIds", List.of("SYN_1"));
                });
    }

    @Test
    void allowsAnotherRequestAfterCustomerProcessingFinishes() {
        PredictionBatchCreateRequest request = new PredictionBatchCreateRequest(
                "201812", List.of("SYN_1"), true);
        long firstBatchId = service.create(request, "admin@miribom.test");
        PredictionBatchService.BatchWork work = service.start(firstBatchId);
        long itemId = work.items().get(0).batchItemId();
        service.markItemRunning(firstBatchId, itemId);
        service.markItemSucceeded(firstBatchId, itemId, 99L, false);
        service.finish(firstBatchId);

        long secondBatchId = service.create(request, "admin@miribom.test");

        assertThat(secondBatchId).isGreaterThan(firstBatchId);
    }
}
