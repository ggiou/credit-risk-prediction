package com.creditrisk.customer.mapper;

import com.creditrisk.customer.dto.CustomerSearchCondition;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * 고객 목록과 현재 예측 요약을 조회한다.
 */
@Mapper
public interface CustomerMapper {

    /** 검색 조건에 맞는 고객 목록을 조회한다. */
    List<Map<String, Object>> findCustomers(@Param("condition") CustomerSearchCondition condition);

    /** 검색 조건에 맞는 전체 고객 수를 조회한다. */
    long countCustomers(@Param("condition") CustomerSearchCondition condition);
}

