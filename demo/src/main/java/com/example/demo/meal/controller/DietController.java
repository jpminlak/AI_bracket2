package com.example.demo.meal.controller;

import com.example.demo.food.model.Food;
import com.example.demo.food.Repository.FoodRepository;
import com.example.demo.meal.DietService;
import com.example.demo.member.Member;
import com.example.demo.member.MemberService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

@RequiredArgsConstructor
@Controller
public class DietController {

    private final DietService dietService;
    private final MemberService memberService;
    private final FoodRepository foodRepository;

    /** 식단추천 폼 */
    @GetMapping("/diet")
    public String dietForm(Model model, Authentication auth) {
        model.addAttribute("today", LocalDate.now());
        Member me = resolveCurrentMember(auth);
        LocalDateTime todayStart = LocalDate.now().atStartOfDay();

        List<Food> breakfastList = fillToFive(
                foodRepository.findTop5ByMember_NumAndMealTimeAndRegDateAfterOrderByRegDateDesc(me.getNum(), "breakfast", todayStart));
        List<Food> lunchList = fillToFive(
                foodRepository.findTop5ByMember_NumAndMealTimeAndRegDateAfterOrderByRegDateDesc(me.getNum(), "lunch", todayStart));
        List<Food> dinnerList = fillToFive(
                foodRepository.findTop5ByMember_NumAndMealTimeAndRegDateAfterOrderByRegDateDesc(me.getNum(), "dinner", todayStart));

        model.addAttribute("breakfastList", breakfastList);
        model.addAttribute("lunchList", lunchList);
        model.addAttribute("dinnerList", dinnerList);

        // ✅ 총 칼로리 합산
        double totalCalories = sumCalories(breakfastList) + sumCalories(lunchList) + sumCalories(dinnerList);
        model.addAttribute("totalCalories", totalCalories);

        return "meal/diet";
    }

    /** 리스트를 항상 5개로 맞추는 헬퍼 */
    private List<Food> fillToFive(List<Food> list) {
        List<Food> result = new ArrayList<>(list);
        while (result.size() < 5) {
            result.add(new Food()); // 기본 생성자로 빈 Food 추가
        }
        return result;
    }

    /** Food 리스트 칼로리 합계 */
    private double sumCalories(List<Food> foods) {
        return foods.stream()
                .filter(f -> f.getCalories() != null)
                .mapToDouble(Food::getCalories)
                .sum();
    }

    /** 추천 실행 */
    @PostMapping("/diet/recommend")
    public String recommend(
            @RequestParam String sex,
            @RequestParam Double height,
            @RequestParam Double weight,
            Authentication auth,
            Model model
    ) {
        Map<String, Object> r = dietService.recommend(sex, height, weight);
        model.addAttribute("r", r);
        return "meal/result";
    }

    /** 추천 저장 */
    @PostMapping("/diet/save")
    public String save(
            @RequestParam String breakfast,
            @RequestParam String lunch,
            @RequestParam String dinner,
            @RequestParam("total_kcal") Integer totalKcal,
            Authentication auth
    ) {
        Member me = resolveCurrentMember(auth);

        Map<String, Object> r = Map.of(
                "breakfast", Map.of("menu", breakfast),
                "lunch",     Map.of("menu", lunch),
                "dinner",    Map.of("menu", dinner),
                "total_kcal", totalKcal
        );
        dietService.saveFromResult(me, r);
        return "redirect:/record";
    }

    @GetMapping("/record")
    public String record(Authentication auth, Model model) {
        Member me = resolveCurrentMember(auth);
        List<com.example.demo.meal.Diet> diets = dietService.findMyDiets(me.getNum());
        model.addAttribute("diets", diets);
        return "meal/record";
    }

    /** 현재 인증된 Member 가져오기 */
    private Member resolveCurrentMember(Authentication auth){
        if (auth == null || auth.getName() == null) {
            throw new IllegalStateException("인증정보 없음");
        }
        String key = auth.getName();
        Optional<Member> byLoginId = memberService.findByMemberId(key);
        if(byLoginId.isPresent()) return byLoginId.get();
        try {
            Long id = Long.valueOf(key);
            Optional<Member> byId = memberService.findByNum(id);
            if (byId.isPresent()) return byId.get();
        } catch (NumberFormatException ignore) { }
        throw new IllegalStateException("회원 없음");
    }
}