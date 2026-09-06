package com.creditrisk.common.web;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BulkSearchValuesTest {

    @Test
    void trimsRemovesBlankAndDeduplicatesWhileKeepingOrder() {
        assertThat(BulkSearchValues.normalize(
                List.of(" SYN_2 ", "", "SYN_1", "SYN_2"), "customerIds"))
                .containsExactly("SYN_2", "SYN_1");
    }

    @Test
    void returnsNullWhenBulkSearchHasNoUsableValue() {
        assertThat(BulkSearchValues.normalize(null, "customerIds")).isNull();
        assertThat(BulkSearchValues.normalize(List.of("", "  "), "customerNames")).isNull();
    }

    @Test
    void rejectsMoreThanFiftyDistinctValues() {
        List<String> values = IntStream.rangeClosed(1, 51).mapToObj(index -> "SYN_" + index).toList();

        assertThatThrownBy(() -> BulkSearchValues.normalize(values, "customerIds"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessage("customerIds는 최대 50개까지 조회할 수 있습니다.");
    }
}
