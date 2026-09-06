package com.creditrisk.page;

import org.junit.jupiter.api.Test;
import org.springframework.ui.ConcurrentModel;

import static org.assertj.core.api.Assertions.assertThat;

class PageControllerTest {

    private final PageController controller = new PageController();

    @Test
    void customerPredictionHistoryKeepsCustomerDetailContext() {
        ConcurrentModel model = new ConcurrentModel();

        String view = controller.customerPredictionHistory("SYN_123", model);

        assertThat(view).isEqualTo("customer/prediction-history");
        assertThat(model.getAttribute("menu")).isEqualTo("customers");
        assertThat(model.getAttribute("customerId")).isEqualTo("SYN_123");
        assertThat(model.getAttribute("activeTab")).isEqualTo("predictions");
    }

    @Test
    void globalPredictionHistoryRemainsAvailable() {
        ConcurrentModel model = new ConcurrentModel();

        String view = controller.predictionHistory(model);

        assertThat(view).isEqualTo("prediction/history");
        assertThat(model.getAttribute("menu")).isEqualTo("predictions");
    }

    @Test
    void batchAdminPageIsAvailableWithoutAddingARegularMenuState() {
        ConcurrentModel model = new ConcurrentModel();

        String view = controller.predictionBatchAdmin(model);

        assertThat(view).isEqualTo("admin/prediction-batches");
        assertThat(model.getAttribute("menu")).isEqualTo("");
    }
}
