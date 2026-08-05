package com.creditrisk.meta.mapper;

import org.apache.ibatis.annotations.Mapper;

import java.util.List;

/**
 * BO 화면 공통 선택값을 데이터베이스에서 조회한다.
 */
@Mapper
public interface MetaMapper {

    /**
     * 피처 스냅샷에 존재하는 기준년월을 최신순으로 조회한다.
     *
     * @return 기준년월 목록
     */
    List<String> findBaseMonths();
}

