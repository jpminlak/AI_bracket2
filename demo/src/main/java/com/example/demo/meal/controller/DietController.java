package com.example.demo.meal.controller;

import org.springframework.http.*;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

@Controller
@RequestMapping("/diet")
public class DietController {

    private final RestTemplate rest = new RestTemplate();

    // FastAPI 실제 모델 호출 강제
    private final String FASTAPI_URL = "http://localhost:8010/recommend?live=true";


    @GetMapping
    public String form(Model model) {
        model.addAttribute("today", LocalDate.now().toString());
        model.addAttribute("gender", "female");
        model.addAttribute("age", 21);
        model.addAttribute("height", 165);
        model.addAttribute("weight", 70);
        return "diet/diet";
    }

    @PostMapping("/recommend")
    public String recommend(@RequestParam String gender,
                            @RequestParam int age,
                            @RequestParam("height") double heightCm,
                            @RequestParam("weight") double weightKg,
                            Model model) {

        // 전날 '아침'만 예시 (탄수 부족)
        Map<String, Object> prevBreakfast = new HashMap<>();
        prevBreakfast.put("carbs_g", 10);
        prevBreakfast.put("protein_g", 8);
        prevBreakfast.put("fat_g", 6);
        prevBreakfast.put("fiber_g", 2);
        prevBreakfast.put("sodium_mg", 500);

        Map<String, Object> payload = new HashMap<>();
        payload.put("gender", gender);
        payload.put("age", age);
        payload.put("height_cm", heightCm);
        payload.put("weight_kg", weightKg);
        payload.put("previous_day", Map.of("breakfast", prevBreakfast));
        payload.put("note", "견과류 알레르기 없음. 한국식 선호.");

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(payload, headers);

        Map<String, Object> result;
        try {
            ResponseEntity<Map> res = rest.postForEntity(FASTAPI_URL, entity, Map.class);
            result = res.getBody();
        } catch (Exception e) {
            // FastAPI 실패 대비 데모 안전값
            result = new HashMap<>();
            result.put("comment", "서버 예시 결과를 표시합니다. FastAPI가 꺼져 있거나 모델 호출 실패.");
            result.put("breakfast", Map.of("menu","현미밥+계란 2개", "kcal", 500));
            result.put("lunch", Map.of("menu","닭가슴살 샐러드", "kcal", 650));
            result.put("dinner", Map.of("menu","연어구이+잡곡밥", "kcal", 550));
            result.put("total_kcal", 1700);
            result.put("goal_calories", 1700);
            result.put("date", LocalDate.now().toString());
        }

        model.addAttribute("r", result);
        return "diet/result";
    }
}
