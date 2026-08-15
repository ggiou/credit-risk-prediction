package com.creditrisk.customer.mapper;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * 고객 상세 탭에 필요한 고객과 월별 금융 데이터를 조회한다.
 */
@Mapper
public interface CustomerDetailMapper {

    /** 고객 존재 여부를 조회한다. */
    boolean existsCustomer(@Param("customerId") String customerId);

    /** 고객 요약 탭의 기준월 데이터를 조회한다. */
    Map<String, Object> findCustomerSummary(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("modelVersion") String modelVersion);

    /** 고객의 최근 위험률 추이를 조회한다. */
    List<Map<String, Object>> findRiskTrend(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("modelVersion") String modelVersion,
            @Param("months") int months);

    /** 월별 카드 이용 데이터를 조회한다. */
    List<Map<String, Object>> findCardUsage(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("months") int months);

    /** 월별 청구 데이터를 조회한다. */
    List<Map<String, Object>> findBilling(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("months") int months);

    /** 월별 신용 및 한도 데이터를 조회한다. */
    List<Map<String, Object>> findCredit(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("months") int months);

    /** 월별 카드 관련 잔액 데이터를 조회한다. */
    List<Map<String, Object>> findBalance(
            @Param("customerId") String customerId,
            @Param("baseYm") String baseYm,
            @Param("months") int months);
}

