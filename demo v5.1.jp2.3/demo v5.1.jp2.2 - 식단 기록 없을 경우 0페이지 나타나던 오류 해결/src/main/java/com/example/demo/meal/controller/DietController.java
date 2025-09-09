// src/main/java/com/example/demo/meal/controller/DietController.java
package com.example.demo.meal.controller;

import com.example.demo.food.Repository.FoodRepository;
import com.example.demo.food.model.Food;
import com.example.demo.meal.AuthUtils;
import com.example.demo.meal.DietService;
import com.example.demo.member.Member;
import com.example.demo.member.MemberService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.lang.reflect.Method;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

@RequiredArgsConstructor
@Controller
public class DietController {

    private final MemberService memberService;
    private final DietService dietService;
    private final FoodRepository foodRepository;

    /** 식단 입력 폼: 뷰에서 참조하는 모델 값을 기본 세팅(Null 방지) */
    @GetMapping("/diet")
    public String dietForm(Authentication auth, Model model) {
        // 화면 헤더에서 today, totalCalories, *List들을 참조하므로 기본값 필수
        if (!model.containsAttribute("today")) {
            model.addAttribute("today", LocalDate.now().toString());
        }
        if (!model.containsAttribute("totalCalories")) {
            model.addAttribute("totalCalories", 0);
        }
        if (!model.containsAttribute("breakfastList")) {
            model.addAttribute("breakfastList", Collections.emptyList());
        }
        if (!model.containsAttribute("lunchList")) {
            model.addAttribute("lunchList", Collections.emptyList());
        }
        if (!model.containsAttribute("dinnerList")) {
            model.addAttribute("dinnerList", Collections.emptyList());
        }
        return "meal/diet";
    }

    /** 식단 추천: 신체정보 + 전날 섭취기록을 FastAPI로 전달 */
    @PostMapping("/diet/recommend")
    public String recommend(
            @RequestParam String sex,
            @RequestParam Double height,
            @RequestParam Double weight,
            Authentication auth,
            Model model
    ) {
        // 로그인 회원
        Member me = AuthUtils.resolveCurrentMember(auth, memberService);

        // 어제 00:00 ~ 오늘 00:00
        LocalDate yesterday = LocalDate.now().minusDays(1);
        LocalDateTime start = yesterday.atStartOfDay();
        LocalDateTime end   = yesterday.plusDays(1).atStartOfDay();

        // 전날 전체 섭취 기록
        List<Food> foods = foodRepository.findByMember_NumAndRegDateBetween(me.getNum(), start, end);

        // FastAPI로 넘길 전날 식단 요약(Map 리스트)
        List<Map<String, Object>> yMeals = new ArrayList<>();
        for (Food f : foods) {
            Map<String, Object> m = new HashMap<>();

            // 이름 (엔티티에 getFoodName()이 일반적)
            String name = Objects.toString(callGetter(f, "getFoodName"), "");
            m.put("name", name);

            // 칼로리 (프로젝트마다 getCalories()/getKcal()/getCalorie() 등 다를 수 있음)
            Number cal = (Number) callGetter(f, "getCalories", "getKcal", "getCalorie");
            m.put("calories", cal != null ? cal : 0);

            // 선택 영양소(있으면 넣기)
            Number p = (Number) callGetter(f, "getProteinG", "getProtein");
            if (p != null) m.put("protein_g", p);

            Number fa = (Number) callGetter(f, "getFatG", "getFat");
            if (fa != null) m.put("fat_g", fa);

            Number c = (Number) callGetter(f, "getCarbG", "getCarbohydrates", "getCarbs");
            if (c != null) m.put("carb_g", c);

            Number fib = (Number) callGetter(f, "getFiberG", "getDietaryFiber");
            if (fib != null) m.put("fiber_g", fib);

            Number s = (Number) callGetter(f, "getSodiumMg", "getSodium");
            if (s != null) m.put("sodium_mg", s);

            yMeals.add(m);
        }

        // FastAPI 호출 (전날 식단 포함)
        Map<String, Object> r = dietService.recommend(sex, height, weight, yMeals);

        model.addAttribute("r", r);
        return "meal/result";
    }

    // ===== 내부 유틸: 리플렉션으로 안전하게 게터 호출(없는 메서드는 무시) =====
    private Object callGetter(Object obj, String... methodNames) {
        if (obj == null) return null;
        for (String m : methodNames) {
            try {
                Method md = obj.getClass().getMethod(m);
                return md.invoke(obj);
            } catch (Exception ignore) {}
        }
        return null;
    }
}
