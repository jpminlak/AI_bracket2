package com.example.demo.meal.controller;

import com.example.demo.food.Repository.FoodRepository;
import com.example.demo.food.model.Food;
import com.example.demo.meal.AuthUtils;
import com.example.demo.meal.Diet;
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
import java.time.Period;
import java.time.format.TextStyle;
import java.util.*;
import java.util.stream.Collectors;

@RequiredArgsConstructor
@Controller
public class DietController {

    private final MemberService memberService;
    private final DietService dietService;
    private final FoodRepository foodRepository;

    @GetMapping("/diet")
    public String dietForm(Authentication auth, Model model) {
        Member me = AuthUtils.resolveCurrentMember(auth, memberService);

        LocalDate today = LocalDate.now();
        String dayOfWeek = today.getDayOfWeek().getDisplayName(TextStyle.FULL, Locale.KOREAN); // "월요일", "화요일" 등
        LocalDateTime start = today.atStartOfDay();
        LocalDateTime end = today.plusDays(1).atStartOfDay();
        int age = Period.between(me.getBirthday(), LocalDate.now()).getYears();

        List<Food> todayFoods = foodRepository.findByMember_NumAndRegDateBetween(me.getNum(), start, end);

        List<Food> breakfastList = new ArrayList<>();
        List<Food> lunchList = new ArrayList<>();
        List<Food> dinnerList = new ArrayList<>();

        double totalCalories = 0;
        for (Food f : todayFoods) {
            if (f.getCalories() != null) {
                totalCalories += f.getCalories();
            }
            switch (f.getMealTime()) {
                case "breakfast" -> breakfastList.add(f);
                case "lunch" -> lunchList.add(f);
                case "dinner" -> dinnerList.add(f);
            }
        }

        // 각 끼니별 영양 정보 계산
        double breakfastCalories = breakfastList.stream().mapToDouble(f -> f.getCalories() != null ? f.getCalories() : 0).sum();
        double breakfastCarbs = breakfastList.stream().mapToDouble(f -> f.getCarbohydrates() != null ? f.getCarbohydrates() : 0).sum();
        double breakfastProtein = breakfastList.stream().mapToDouble(f -> f.getProtein() != null ? f.getProtein() : 0).sum();
        double breakfastFat = breakfastList.stream().mapToDouble(f -> f.getFat() != null ? f.getFat() : 0).sum();

        double lunchCalories = lunchList.stream().mapToDouble(f -> f.getCalories() != null ? f.getCalories() : 0).sum();
        double lunchCarbs = lunchList.stream().mapToDouble(f -> f.getCarbohydrates() != null ? f.getCarbohydrates() : 0).sum();
        double lunchProtein = lunchList.stream().mapToDouble(f -> f.getProtein() != null ? f.getProtein() : 0).sum();
        double lunchFat = lunchList.stream().mapToDouble(f -> f.getFat() != null ? f.getFat() : 0).sum();

        double dinnerCalories = dinnerList.stream().mapToDouble(f -> f.getCalories() != null ? f.getCalories() : 0).sum();
        double dinnerCarbs = dinnerList.stream().mapToDouble(f -> f.getCarbohydrates() != null ? f.getCarbohydrates() : 0).sum();
        double dinnerProtein = dinnerList.stream().mapToDouble(f -> f.getProtein() != null ? f.getProtein() : 0).sum();
        double dinnerFat = dinnerList.stream().mapToDouble(f -> f.getFat() != null ? f.getFat() : 0).sum();

        model.addAttribute("today", today.toString());
        model.addAttribute("dayOfWeek", dayOfWeek);
        model.addAttribute("age", age);
        model.addAttribute("totalCalories", (int) totalCalories);
        model.addAttribute("breakfastList", breakfastList);
        model.addAttribute("breakfastCalories", breakfastCalories);
        model.addAttribute("breakfastCarbs", breakfastCarbs);
        model.addAttribute("breakfastProtein", breakfastProtein);
        model.addAttribute("breakfastFat", breakfastFat);
        model.addAttribute("lunchList", lunchList);
        model.addAttribute("lunchCalories", lunchCalories);
        model.addAttribute("lunchCarbs", lunchCarbs);
        model.addAttribute("lunchProtein", lunchProtein);
        model.addAttribute("lunchFat", lunchFat);
        model.addAttribute("dinnerList", dinnerList);
        model.addAttribute("dinnerCalories", dinnerCalories);
        model.addAttribute("dinnerCarbs", dinnerCarbs);
        model.addAttribute("dinnerProtein", dinnerProtein);
        model.addAttribute("dinnerFat", dinnerFat);

        return "meal/diet";
    }

    /** 다음 한 끼 식사만 추천 */
    @PostMapping("/diet/recommend-next")
    public String recommendNext(
            @RequestParam String sex,
            @RequestParam Integer height,
            @RequestParam Integer weight,
            Authentication auth,
            Model model) {

        Member me = AuthUtils.resolveCurrentMember(auth, memberService);

        // 오늘 기록 조회
        LocalDate today = LocalDate.now();
        LocalDateTime start = today.atStartOfDay();
        LocalDateTime end = today.plusDays(1).atStartOfDay();
        List<Food> todayFoods = foodRepository.findByMember_NumAndRegDateBetween(me.getNum(), start, end);

        // 끼니별 분류
        List<Food> breakfastList = todayFoods.stream()
                .filter(f -> "breakfast".equals(f.getMealTime()))
                .collect(Collectors.toList());
        List<Food> lunchList = todayFoods.stream()
                .filter(f -> "lunch".equals(f.getMealTime()))
                .collect(Collectors.toList());
        List<Food> dinnerList = todayFoods.stream()
                .filter(f -> "dinner".equals(f.getMealTime()))
                .collect(Collectors.toList());

        boolean hasBreakfast = !breakfastList.isEmpty();
        boolean hasLunch = !lunchList.isEmpty();
        boolean hasDinner = !dinnerList.isEmpty();

        // 다음 끼니 결정 로직
        String nextMeal = determineNextMeal(hasBreakfast, hasLunch, hasDinner);

        // 날짜 계산 (다음날 아침인 경우)
        LocalDate targetDate = today;
        if ("breakfast".equals(nextMeal) && (hasDinner || (hasLunch && hasDinner))) {
            targetDate = today.plusDays(1);
        }

        // 일일 권장량 계산 (BMR 기반)
        NutritionRequirement dailyRequirement = calculateDailyRequirement(sex, height, weight);

        // 이미 섭취한 영양소 계산 (실제 입력된 것만)
        NutritionInfo consumedNutrition = calculateConsumedNutrition(todayFoods);

        // 평균 섭취량 가정을 통한 내부 계산
        NutritionInfo assumedConsumed = calculateAssumedConsumedNutrition(
                dailyRequirement, hasBreakfast, hasLunch, hasDinner, nextMeal);

        // 실제 섭취량 + 가정 섭취량
        NutritionInfo totalConsumed = addNutrition(consumedNutrition, assumedConsumed);

        // 다음 끼니 권장량 계산
        NutritionInfo nextMealRequirement = calculateNextMealRequirement(
                dailyRequirement, totalConsumed, nextMeal);

        // 초과 여부 체크
        boolean isExceeded = checkNutritionExceeded(totalConsumed, dailyRequirement);

        // 추천 음식 생성 (간단한 예시)
        List<Food> recommendedFoods = generateRecommendedFoods(nextMealRequirement, nextMeal);

        // 추천 음식의 총 영양소 계산
        NutritionInfo recommendedNutrition = calculateTotalNutrition(recommendedFoods);

        String foodNamesString = recommendedFoods.stream()
                .map(Food::getFoodName)
                .collect(Collectors.joining(", "));

        // 날짜 + 요일 계산
        String dayOfWeekKor = getDayOfWeekKor(targetDate);
        model.addAttribute("dietDate", targetDate.toString());  // DB 저장용
        model.addAttribute("dayOfWeek", dayOfWeekKor);          // 화면 표시용

        // 추천 이유 생성
        String reason = generateRecommendationReason(dailyRequirement, totalConsumed,
                recommendedNutrition, isExceeded, nextMeal);

        model.addAttribute("recommendedFoods", recommendedFoods);
        model.addAttribute("totalCalories", recommendedNutrition.getCalories());
        model.addAttribute("totalCarbs", recommendedNutrition.getCarbohydrates());
        model.addAttribute("totalProtein", recommendedNutrition.getProtein());
        model.addAttribute("totalFat", recommendedNutrition.getFat());
        model.addAttribute("foodNamesString", foodNamesString);
        model.addAttribute("memberName", me.getMemberName());
        model.addAttribute("mealTime", nextMeal);
        model.addAttribute("mealLabel", getMealLabel(nextMeal));
        model.addAttribute("total_kcal", recommendedNutrition.getCalories());
        model.addAttribute("goal_kcal", nextMealRequirement.getCalories());
        model.addAttribute("reason", reason);
        model.addAttribute("isExceeded", isExceeded);
        model.addAttribute("dailyRequirement", dailyRequirement);
        model.addAttribute("consumedTotal", totalConsumed);

        return "meal/result";
    }

    @PostMapping("/diet/save")
    public String saveDiet(
            @RequestParam(name = "breakfast", required = false) String breakfast,
            @RequestParam(name = "lunch", required = false) String lunch,
            @RequestParam(name = "dinner", required = false) String dinner,
            @RequestParam(name = "breakfast_kcal", required = false) Double breakfastKcal,
            @RequestParam(name = "lunch_kcal", required = false) Double lunchKcal,
            @RequestParam(name = "dinner_kcal", required = false) Double dinnerKcal,
            @RequestParam(name = "breakfast_carbs", required = false) Double breakfastCarbs,
            @RequestParam(name = "breakfast_protein", required = false) Double breakfastProtein,
            @RequestParam(name = "breakfast_fat", required = false) Double breakfastFat,
            @RequestParam(name = "lunch_carbs", required = false) Double lunchCarbs,
            @RequestParam(name = "lunch_protein", required = false) Double lunchProtein,
            @RequestParam(name = "lunch_fat", required = false) Double lunchFat,
            @RequestParam(name = "dinner_carbs", required = false) Double dinnerCarbs,
            @RequestParam(name = "dinner_protein", required = false) Double dinnerProtein,
            @RequestParam(name = "dinner_fat", required = false) Double dinnerFat,
            @RequestParam(name = "dietDate") String dietDateStr,
            Authentication auth
    ) {
        Member me = AuthUtils.resolveCurrentMember(auth, memberService);
        LocalDate dietDate = LocalDate.parse(dietDateStr);

        Diet diet = dietService.findTodayDiet(me.getNum(), dietDate);
        if (diet == null) {
            diet = new Diet();
            diet.setMember(me);
            diet.setDietDate(dietDate);
        }

        // --- 메뉴 이름 합치기 ---
        diet.setBreakfast(mergeMeals(diet.getBreakfast(), breakfast));
        diet.setLunch(mergeMeals(diet.getLunch(), lunch));
        diet.setDinner(mergeMeals(diet.getDinner(), dinner));

        // --- 아침 영양소 ---
        if (breakfastKcal != null) diet.setBreakfastKcal(breakfastKcal);
        if (breakfastCarbs != null) diet.setBreakfastCarbs(breakfastCarbs);
        if (breakfastProtein != null) diet.setBreakfastProtein(breakfastProtein);
        if (breakfastFat != null) diet.setBreakfastFat(breakfastFat);

        // --- 점심 영양소 ---
        if (lunchKcal != null) diet.setLunchKcal(lunchKcal);
        if (lunchCarbs != null) diet.setLunchCarbs(lunchCarbs);
        if (lunchProtein != null) diet.setLunchProtein(lunchProtein);
        if (lunchFat != null) diet.setLunchFat(lunchFat);

        // --- 저녁 영양소 ---
        if (dinnerKcal != null) diet.setDinnerKcal(dinnerKcal);
        if (dinnerCarbs != null) diet.setDinnerCarbs(dinnerCarbs);
        if (dinnerProtein != null) diet.setDinnerProtein(dinnerProtein);
        if (dinnerFat != null) diet.setDinnerFat(dinnerFat);

        // --- 총 칼로리 다시 계산 ---
        double totalKcal =
                defaultZero(diet.getBreakfastKcal()) +
                        defaultZero(diet.getLunchKcal()) +
                        defaultZero(diet.getDinnerKcal());
        diet.setTotalKcal(totalKcal);

        dietService.saveDiet(diet);

        System.out.println("✅ saveDiet input:");
        System.out.println("breakfast = " + breakfast);
        System.out.println("lunch = " + lunch);
        System.out.println("dinner = " + dinner);

        return "redirect:/record/calendar";
    }

    // ========== 헬퍼 메서드들 ==========

    private String determineNextMeal(boolean hasBreakfast, boolean hasLunch, boolean hasDinner) {
        if (hasBreakfast && hasLunch && hasDinner) {
            return "breakfast"; // 다음날 아침
        } else if (hasBreakfast && hasLunch) {
            return "dinner";
        } else if (hasLunch && hasDinner) {
            return "breakfast"; // 다음날 아침
        } else if (hasBreakfast && !hasLunch) {
            return "lunch";
        } else if (hasLunch && !hasDinner) {
            return "dinner";
        } else if (hasDinner && !hasBreakfast) {
            return "breakfast"; // 다음날 아침
        } else if (!hasBreakfast && !hasLunch && !hasDinner) {
            return "breakfast"; // 아무것도 없으면 아침부터
        } else {
            return "lunch"; // 기본값
        }
    }

    private NutritionRequirement calculateDailyRequirement(String sex, Integer height, Integer weight) {
        // BMR 계산 (Mifflin-St Jeor 방정식)
        double bmr;
        if ("남".equals(sex) || "male".equals(sex.toLowerCase())) {
            bmr = 10 * weight + 6.25 * height - 5 * 21 + 5; // 나이 21세 가정
        } else {
            bmr = 10 * weight + 6.25 * height - 5 * 21 - 161;
        }

        double tdee = bmr * 1.375; // 가벼운 활동 수준

        // 영양소 비율: 탄수화물 50%, 단백질 25%, 지방 25%
        double carbs = tdee * 0.5 / 4; // 1g = 4kcal
        double protein = tdee * 0.25 / 4; // 1g = 4kcal
        double fat = tdee * 0.25 / 9; // 1g = 9kcal

        return new NutritionRequirement(tdee, carbs, protein, fat);
    }

    private NutritionInfo calculateConsumedNutrition(List<Food> foods) {
        double calories = foods.stream().mapToDouble(f -> f.getCalories() != null ? f.getCalories() : 0).sum();
        double carbs = foods.stream().mapToDouble(f -> f.getCarbohydrates() != null ? f.getCarbohydrates() : 0).sum();
        double protein = foods.stream().mapToDouble(f -> f.getProtein() != null ? f.getProtein() : 0).sum();
        double fat = foods.stream().mapToDouble(f -> f.getFat() != null ? f.getFat() : 0).sum();

        return new NutritionInfo(calories, carbs, protein, fat);
    }

    private NutritionInfo calculateAssumedConsumedNutrition(
            NutritionRequirement dailyReq, boolean hasBreakfast, boolean hasLunch,
            boolean hasDinner, String nextMeal) {

        double assumedCalories = 0;
        double assumedCarbs = 0;
        double assumedProtein = 0;
        double assumedFat = 0;

        // 각 끼니별 평균 비율: 아침 25%, 점심 40%, 저녁 35%
        if (!hasBreakfast && !"breakfast".equals(nextMeal)) {
            assumedCalories += dailyReq.getCalories() * 0.25;
            assumedCarbs += dailyReq.getCarbohydrates() * 0.25;
            assumedProtein += dailyReq.getProtein() * 0.25;
            assumedFat += dailyReq.getFat() * 0.25;
        }
        if (!hasLunch && !"lunch".equals(nextMeal)) {
            assumedCalories += dailyReq.getCalories() * 0.40;
            assumedCarbs += dailyReq.getCarbohydrates() * 0.40;
            assumedProtein += dailyReq.getProtein() * 0.40;
            assumedFat += dailyReq.getFat() * 0.40;
        }
        if (!hasDinner && !"dinner".equals(nextMeal)) {
            assumedCalories += dailyReq.getCalories() * 0.35;
            assumedCarbs += dailyReq.getCarbohydrates() * 0.35;
            assumedProtein += dailyReq.getProtein() * 0.35;
            assumedFat += dailyReq.getFat() * 0.35;
        }

        return new NutritionInfo(assumedCalories, assumedCarbs, assumedProtein, assumedFat);
    }

    private NutritionInfo addNutrition(NutritionInfo a, NutritionInfo b) {
        return new NutritionInfo(
                a.getCalories() + b.getCalories(),
                a.getCarbohydrates() + b.getCarbohydrates(),
                a.getProtein() + b.getProtein(),
                a.getFat() + b.getFat()
        );
    }

    private NutritionInfo calculateNextMealRequirement(
            NutritionRequirement dailyReq, NutritionInfo consumed, String nextMeal) {

        double remainingCalories = Math.max(0, dailyReq.getCalories() - consumed.getCalories());
        double remainingCarbs = Math.max(0, dailyReq.getCarbohydrates() - consumed.getCarbohydrates());
        double remainingProtein = Math.max(0, dailyReq.getProtein() - consumed.getProtein());
        double remainingFat = Math.max(0, dailyReq.getFat() - consumed.getFat());

        // 최소 권장량 설정 (너무 적으면 기본값으로)
        if (remainingCalories < 200) remainingCalories = 200;
        if (remainingCarbs < 20) remainingCarbs = 20;
        if (remainingProtein < 10) remainingProtein = 10;
        if (remainingFat < 5) remainingFat = 5;

        return new NutritionInfo(remainingCalories, remainingCarbs, remainingProtein, remainingFat);
    }

    private boolean checkNutritionExceeded(NutritionInfo consumed, NutritionRequirement required) {
        return consumed.getCalories() > required.getCalories() * 1.1; // 10% 초과시 초과로 판단
    }

    private List<Food> generateRecommendedFoods(NutritionInfo requirement, String mealType) {
        List<Food> foods = new ArrayList<>();

        // 간단한 메뉴 추천 로직 (실제로는 더 복잡한 로직 필요)
        switch (mealType) {
            case "breakfast":
                foods.add(createFood("현미밥", requirement.getCalories() * 0.4,
                        requirement.getCarbohydrates() * 0.5, requirement.getProtein() * 0.2, requirement.getFat() * 0.1));
                foods.add(createFood("달걀찜", requirement.getCalories() * 0.3,
                        requirement.getCarbohydrates() * 0.1, requirement.getProtein() * 0.5, requirement.getFat() * 0.4));
                foods.add(createFood("시금치나물", requirement.getCalories() * 0.2,
                        requirement.getCarbohydrates() * 0.3, requirement.getProtein() * 0.2, requirement.getFat() * 0.3));
                foods.add(createFood("김치", requirement.getCalories() * 0.1,
                        requirement.getCarbohydrates() * 0.1, requirement.getProtein() * 0.1, requirement.getFat() * 0.2));
                break;
            case "lunch":
                foods.add(createFood("현미밥", requirement.getCalories() * 0.35,
                        requirement.getCarbohydrates() * 0.4, requirement.getProtein() * 0.15, requirement.getFat() * 0.1));
                foods.add(createFood("닭가슴살구이", requirement.getCalories() * 0.4,
                        requirement.getCarbohydrates() * 0.05, requirement.getProtein() * 0.6, requirement.getFat() * 0.3));
                foods.add(createFood("브로콜리", requirement.getCalories() * 0.15,
                        requirement.getCarbohydrates() * 0.3, requirement.getProtein() * 0.15, requirement.getFat() * 0.2));
                foods.add(createFood("된장국", requirement.getCalories() * 0.1,
                        requirement.getCarbohydrates() * 0.25, requirement.getProtein() * 0.1, requirement.getFat() * 0.4));
                break;
            case "dinner":
                foods.add(createFood("잡곡밥", requirement.getCalories() * 0.3,
                        requirement.getCarbohydrates() * 0.45, requirement.getProtein() * 0.15, requirement.getFat() * 0.1));
                foods.add(createFood("연어구이", requirement.getCalories() * 0.35,
                        requirement.getCarbohydrates() * 0.02, requirement.getProtein() * 0.5, requirement.getFat() * 0.4));
                foods.add(createFood("구운채소", requirement.getCalories() * 0.25,
                        requirement.getCarbohydrates() * 0.4, requirement.getProtein() * 0.2, requirement.getFat() * 0.3));
                foods.add(createFood("미역국", requirement.getCalories() * 0.1,
                        requirement.getCarbohydrates() * 0.13, requirement.getProtein() * 0.15, requirement.getFat() * 0.2));
                break;
        }

        return foods;
    }

    private Food createFood(String name, double calories, double carbs, double protein, double fat) {
        Food food = new Food();
        food.setFoodName(name);
        food.setCalories(Math.round(calories * 10.0) / 10.0);
        food.setCarbohydrates(Math.round(carbs * 10.0) / 10.0);
        food.setProtein(Math.round(protein * 10.0) / 10.0);
        food.setFat(Math.round(fat * 10.0) / 10.0);
        return food;
    }

    private NutritionInfo calculateTotalNutrition(List<Food> foods) {
        double calories = foods.stream().mapToDouble(f -> f.getCalories() != null ? f.getCalories() : 0).sum();
        double carbs = foods.stream().mapToDouble(f -> f.getCarbohydrates() != null ? f.getCarbohydrates() : 0).sum();
        double protein = foods.stream().mapToDouble(f -> f.getProtein() != null ? f.getProtein() : 0).sum();
        double fat = foods.stream().mapToDouble(f -> f.getFat() != null ? f.getFat() : 0).sum();

        return new NutritionInfo(calories, carbs, protein, fat);
    }

    private String generateRecommendationReason(NutritionRequirement dailyReq, NutritionInfo consumed,
                                                NutritionInfo recommended, boolean isExceeded, String nextMeal) {

        if (isExceeded) {
            return String.format("일일 권장량을 초과하여 섭취하셨습니다. 다음 %s는 가벼운 식단으로 조절하시는 것을 권장합니다. " +
                            "권장: %.0f kcal, 현재까지: %.0f kcal",
                    getMealLabel(nextMeal), dailyReq.getCalories(), consumed.getCalories());
        } else {
            double remaining = dailyReq.getCalories() - consumed.getCalories();
            return String.format("일일 권장량 %.0f kcal 중 %.0f kcal가 남아있어 %s로 %.0f kcal를 권장합니다. " +
                            "균형잡힌 영양소 섭취를 위해 탄수화물, 단백질, 지방을 고르게 배분했습니다.",
                    dailyReq.getCalories(), remaining, getMealLabel(nextMeal), recommended.getCalories());
        }
    }

    private String getDayOfWeekKor(LocalDate date) {
        return switch (date.getDayOfWeek()) {
            case MONDAY -> "월요일";
            case TUESDAY -> "화요일";
            case WEDNESDAY -> "수요일";
            case THURSDAY -> "목요일";
            case FRIDAY -> "금요일";
            case SATURDAY -> "토요일";
            case SUNDAY -> "일요일";
        };
    }

    private String getMealLabel(String mealType) {
        return switch (mealType) {
            case "breakfast" -> "아침";
            case "lunch" -> "점심";
            case "dinner" -> "저녁";
            default -> "";
        };
    }

    private String mergeMeals(String existing, String incoming) {
        if (existing == null || existing.isEmpty()) return incoming != null ? incoming : "";
        if (incoming == null || incoming.isEmpty()) return existing;
        return existing + ", " + incoming;
    }

    private double defaultZero(Double val) {
        return val != null ? val : 0;
    }

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

    // ========== 내부 클래스들 ==========

    public static class NutritionRequirement {
        private final double calories;
        private final double carbohydrates;
        private final double protein;
        private final double fat;

        public NutritionRequirement(double calories, double carbohydrates, double protein, double fat) {
            this.calories = calories;
            this.carbohydrates = carbohydrates;
            this.protein = protein;
            this.fat = fat;
        }

        public double getCalories() { return calories; }
        public double getCarbohydrates() { return carbohydrates; }
        public double getProtein() { return protein; }
        public double getFat() { return fat; }
    }

    public static class NutritionInfo {
        private final double calories;
        private final double carbohydrates;
        private final double protein;
        private final double fat;

        public NutritionInfo(double calories, double carbohydrates, double protein, double fat) {
            this.calories = calories;
            this.carbohydrates = carbohydrates;
            this.protein = protein;
            this.fat = fat;
        }

        public double getCalories() { return calories; }
        public double getCarbohydrates() { return carbohydrates; }
        public double getProtein() { return protein; }
        public double getFat() { return fat; }
    }
}