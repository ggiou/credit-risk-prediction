package com.creditrisk.customer.service;

import com.creditrisk.common.api.PageData;
import com.creditrisk.common.domain.RiskGrade;
import com.creditrisk.customer.dto.CustomerListItem;
import com.creditrisk.customer.dto.CustomerSearchCondition;
import com.creditrisk.customer.mapper.CustomerMapper;
import com.creditrisk.meta.service.MetaService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.Instant;
import java.time.YearMonth;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * 고객 검색 조건을 정리하고 목록 응답을 구성한다.
 */
@Service
public class CustomerService {

    private static final DateTimeFormatter BASE_YM_FORMAT = DateTimeFormatter.ofPattern("yyyyMM");

    private final CustomerMapper customerMapper;
    private final MetaService metaService;
    private final String modelVersion;

    /** 고객 조회 의존성과 활성 모델 버전을 주입받는다. */
    public CustomerService(
            CustomerMapper customerMapper,
            MetaService metaService,
            @Value("${ai.model.version}") String modelVersion) {
        this.customerMapper = customerMapper;
        this.metaService = metaService;
        this.modelVersion = modelVersion;
    }

    /**
     * 검색 조건에 맞는 고객과 현재 예측 결과를 페이지로 조회한다.
     */
    public PageData<CustomerListItem> searchCustomers(
            String requestedBaseYm,
            String customerId,
            RiskGrade riskGrade,
            String analysisStatus,
            int horizon,
            Double minRiskRate,
            Double maxRiskRate,
            int page,
            int size,
            String sort) {
        // 검색 기준월과 이전 기준월을 한 번 계산해 목록과 건수 쿼리에 동일하게 전달한다.
        String baseYm = metaService.resolveBaseYm(requestedBaseYm);
        String previousBaseYm = YearMonth.parse(baseYm, BASE_YM_FORMAT).minusMonths(1).format(BASE_YM_FORMAT);
        String[] sortParts = sort.split(",");

        CustomerSearchCondition condition = new CustomerSearchCondition(
                baseYm,
                previousBaseYm,
                blankToNull(customerId),
                riskGrade == null ? null : riskGrade.getDisplayName(),
                blankToNull(analysisStatus),
                horizon,
                minRiskRate,
                maxRiskRate,
                page,
                size,
                page * size,
                sortParts[0],
                sortParts[1].toUpperCase(),
                modelVersion);

        List<CustomerListItem> items = customerMapper.findCustomers(condition).stream()
                .map(this::toListItem)
                .toList();
        long totalElements = customerMapper.countCustomers(condition);
        return PageData.of(items, page, size, totalElements);
    }

    /**
     * MyBatis 조회 행을 고객 목록 DTO로 변환한다.
     */
    private CustomerListItem toListItem(Map<String, Object> row) {
        // 예측 미실행 고객의 null 위험률과 예측 ID는 그대로 보존한다.
        return new CustomerListItem(
                stringValue(row.get("customerId")),
                nullableString(row.get("displayName")),
                stringValue(row.get("baseYm")),
                nullableLong(row.get("predictionId")),
                stringValue(row.get("analysisStatus")),
                nullableString(row.get("riskGrade")),
                nullableString(row.get("riskGradeName")),
                nullableDouble(row.get("hazard1m")),
                nullableDouble(row.get("hazard2m")),
                nullableDouble(row.get("hazard3m")),
                nullableDouble(row.get("riskChange3m")),
                nullableString(row.get("primaryRiskFactor")),
                instantValue(row.get("predictedAt")));
    }

    /** 공백 문자열을 선택하지 않은 조건으로 변환한다. */
    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    /** DB 값을 문자열로 변환한다. */
    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    /** null을 보존하면서 DB 값을 문자열로 변환한다. */
    private String nullableString(Object value) {
        return value == null ? null : String.valueOf(value);
    }

    /** null을 보존하면서 DB 숫자를 Long으로 변환한다. */
    private Long nullableLong(Object value) {
        return value instanceof Number number ? number.longValue() : null;
    }

    /** null을 보존하면서 DB 숫자를 Double로 변환한다. */
    private Double nullableDouble(Object value) {
        return value instanceof Number number ? number.doubleValue() : null;
    }

    /** JDBC Timestamp를 API의 UTC 시각으로 변환한다. */
    private Instant instantValue(Object value) {
        return value instanceof Timestamp timestamp ? timestamp.toInstant() : null;
    }
}
