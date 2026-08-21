package com.creditrisk.page;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;

import java.util.Map;

/**
 * BO 화면별 JSP 경로와 고객·탭 정보를 연결한다.
 */
@Controller
@RequestMapping
public class PageController {

    private static final Map<String, String> FINANCIAL_NAMES = Map.of(
            "card-usage", "카드 이용",
            "billing", "청구",
            "credit", "신용",
            "balance", "잔액");

    /** 대시보드 화면을 반환한다. */
    @GetMapping("/")
    public String dashboard(Model model) {
        // 사이드바의 대시보드 메뉴를 활성화한다.
        model.addAttribute("menu", "dashboard");
        return "dashboard";
    }

    /** 고객 검색 목록 화면을 반환한다. */
    @GetMapping("/customers")
    public String customerList(Model model) {
        // 사이드바의 고객 관리 메뉴를 활성화한다.
        model.addAttribute("menu", "customers");
        return "customer/list";
    }

    /** 고객 상세 기본 경로를 요약 화면으로 이동한다. */
    @GetMapping("/customers/{customerId}")
    public String customerDetail(@PathVariable String customerId) {
        // 상세 진입 시 먼저 전체 위험과 금융 요약을 보여준다.
        return "redirect:/customers/" + customerId + "/summary";
    }

    /** 고객 요약 화면을 반환한다. */
    @GetMapping("/customers/{customerId}/summary")
    public String customerSummary(@PathVariable String customerId, Model model) {
        // 공통 고객 탭에 고객번호와 활성 탭을 전달한다.
        addCustomerModel(model, customerId, "summary");
        return "customer/summary";
    }

    /** 카드 이용·청구·신용·잔액 중 선택한 월별 금융 화면을 반환한다. */
    @GetMapping("/customers/{customerId}/financials/{financialType}")
    public String customerFinancial(
            @PathVariable String customerId,
            @PathVariable String financialType,
            Model model) {
        if (!FINANCIAL_NAMES.containsKey(financialType)) {
            // 존재하지 않는 탭은 JSP를 추측해 열지 않고 고객 요약으로 되돌린다.
            return "redirect:/customers/" + customerId + "/summary";
        }
        addCustomerModel(model, customerId, "financials");
        model.addAttribute("financialType", financialType);
        model.addAttribute("financialName", FINANCIAL_NAMES.get(financialType));
        return "customer/financial";
    }

    /** 고객 AI 분석 결과 화면을 반환한다. */
    @GetMapping("/customers/{customerId}/ai-analysis")
    public String customerAiAnalysis(@PathVariable String customerId, Model model) {
        // 현재 예측이 없으면 같은 화면에서 분석 실행 버튼을 표시한다.
        addCustomerModel(model, customerId, "ai-analysis");
        return "customer/ai-analysis";
    }

    /** 전체 고객 예측 이력 화면을 반환한다. */
    @GetMapping("/predictions")
    public String predictionHistory(Model model) {
        // 사이드바의 예측 관리 메뉴를 활성화한다.
        model.addAttribute("menu", "predictions");
        return "prediction/history";
    }

    /** 고객 상세 화면이 공통으로 사용하는 모델 속성을 추가한다. */
    private void addCustomerModel(Model model, String customerId, String activeTab) {
        // JSP와 JavaScript가 URL을 다시 해석하지 않도록 서버에서 명시적으로 전달한다.
        model.addAttribute("menu", "customers");
        model.addAttribute("customerId", customerId);
        model.addAttribute("activeTab", activeTab);
    }
}

