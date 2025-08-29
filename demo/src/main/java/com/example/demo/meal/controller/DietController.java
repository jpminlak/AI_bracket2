package com.example.demo.meal.controller;

import com.example.demo.member.Member;
import com.example.demo.member.MemberRepository;
import com.example.demo.member.MemberService;
import org.apache.catalina.User;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@Controller
@RequestMapping("/diet")
public class DietController {
    MemberService memberService;

    @Value("${diet.api-base}")
    private String apiBase;     // 예: http://127.0.0.1:8001


    // 간단 버전: 컨트롤러 내부에서 RestTemplate 생성
    private final RestTemplate rest = new RestTemplate();

    /** 폼 페이지 */
    @GetMapping
    public String form(Model model, RedirectAttributes re) {
        model.addAttribute("today", java.time.LocalDate.now().toString());
        model.addAttribute("gender", "female");
        model.addAttribute("age", 29);
        model.addAttribute("height", 165);
        model.addAttribute("weight", 62);

        return "meal/diet";
    }

    /** 추천 실행: 항상 라이브로 호출 + 전날식단(아침만) 예시 보정 포함 */
    @PostMapping("/recommend")
    public String recommend(

            @RequestParam String gender,
            @RequestParam Integer age,
            @RequestParam(name = "height") Double heightCm,
            @RequestParam(name = "weight") Double weightKg,
            Model model
    ) {


        // FastAPI 요청 바디(JSON) — 키 이름 중요
        Map<String, Object> body = new HashMap<>();
        body.put("gender", gender);
        body.put("age", age);
        body.put("height_cm", heightCm);
        body.put("weight_kg", weightKg);

        // 전날식단 예시(아침만 보정: 탄수 부족 가정) — 데모용
        Map<String, Object> prevBreakfast = new HashMap<>();
        prevBreakfast.put("carbs_g", 30);
        prevBreakfast.put("protein_g", 20);
        prevBreakfast.put("fat_g", 10);
        prevBreakfast.put("fiber_g", 5);
        prevBreakfast.put("sodium_mg", 700);
        Map<String, Object> previousDay = new HashMap<>();
        previousDay.put("breakfast", prevBreakfast);
        body.put("previous_day", previousDay);

        // 항상 라이브 호출
        String url = UriComponentsBuilder
                .fromHttpUrl(apiBase + "/recommend")
                .queryParam("live", true)
                .toUriString();

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> req = new HttpEntity<>(body, headers);

        Map<String, Object> r;
        try {
            ResponseEntity<Map> resp = rest.exchange(url, HttpMethod.POST, req, Map.class);
            r = (resp.getStatusCode().is2xxSuccessful() && resp.getBody() != null)
                    ? resp.getBody() : fallback();
        } catch (Exception e) {
            r = fallback();
        }

        model.addAttribute("r", r);
        return "meal/result";
    }

    /** FastAPI 실패 시 폴백(영양소 포함) */
    private Map<String, Object> fallback() {
        Map<String, Object> r = new HashMap<>();
        r.put("date", java.time.LocalDate.now().toString());
        r.put("goal_calories", 1700);
        r.put("comment", "서버 예시 결과를 표시합니다. FastAPI가 꺼져 있거나 모델 호출 실패.");

        Map<String, Object> b = new HashMap<>();
        b.put("menu", "현미밥 150g + 계란 2개");
        b.put("kcal", 500);
        Map<String, Object> nb = new HashMap<>();
        nb.put("carbs_g", 60); nb.put("protein_g", 28);
        nb.put("fat_g", 18);   nb.put("fiber_g", 6);  nb.put("sodium_mg", 900);
        b.put("nutrients", nb);

        Map<String, Object> l = new HashMap<>();
        l.put("menu", "닭가슴살 샐러드 + 고구마 150g");
        l.put("kcal", 650);
        Map<String, Object> nl = new HashMap<>();
        nl.put("carbs_g", 55); nl.put("protein_g", 35);
        nl.put("fat_g", 15);   nl.put("fiber_g", 8);  nl.put("sodium_mg", 850);
        l.put("nutrients", nl);

        Map<String, Object> d = new HashMap<>();
        d.put("menu", "잡곡밥 120g + 연어구이 120g");
        d.put("kcal", 550);
        Map<String, Object> nd = new HashMap<>();
        nd.put("carbs_g", 45); nd.put("protein_g", 32);
        nd.put("fat_g", 16);   nd.put("fiber_g", 7);  nd.put("sodium_mg", 950);
        d.put("nutrients", nd);

        r.put("breakfast", b);
        r.put("lunch", l);
        r.put("dinner", d);
        r.put("total_kcal", 1700);
        return r;
    }
}
