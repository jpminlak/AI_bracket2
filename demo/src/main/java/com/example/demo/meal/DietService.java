package com.example.demo.meal;

import com.example.demo.member.Member;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDate;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RequiredArgsConstructor
@Service
public class DietService {

    private final DietRepository dietRepository;
    private final RestTemplate restTemplate = new RestTemplate();

    // FastAPI 추천 엔드포인트 (미지정 시 기본값)
    @Value("${fastapi.recommend.url:http://127.0.0.1:8001/recommend?live=true}")
    private String fastApiRecommendUrl;

    /** 기존 호환: 전날 식단 없이 호출 */
    public Map<String, Object> recommend(String sex, Integer height, Integer weight) {
        return recommend(sex, height, weight, Collections.emptyList());
    }
    /** 다음 식사 추천 호출 */
    public Map<String, Object> recommendNext(String sex,
                                             Integer height,
                                             Integer weight,
                                             String nextMeal,
                                             String todayMeals) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("gender", toGenderEn(sex));  // FastAPI 요구
        payload.put("age", 21);
        payload.put("height_cm", height);
        payload.put("weight_kg", weight);
        payload.put("activity_level", "light");
        payload.put("meal_type", nextMeal);
        payload.put("today_meals", todayMeals);

        String url = "http://127.0.0.1:8001/recommend/next";
        Map resp = restTemplate.postForObject(url, payload, Map.class);
        if (resp == null) resp = new HashMap<>();
        return resp;
    }

    // 전날 식단 포함 오버로드
    public Map<String, Object> recommend(String sex,
                                         Integer height,
                                         Integer weight,
                                         List<Map<String, Object>> yesterdayMeals) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("gender", toGenderEn(sex));
        payload.put("age", 21);
        payload.put("height_cm", height);
        payload.put("weight_kg", weight);
        payload.put("activity_level", "light");

        if (yesterdayMeals != null && !yesterdayMeals.isEmpty()) {
            payload.put("yesterday_meals", yesterdayMeals);
        }

        Map resp = restTemplate.postForObject(fastApiRecommendUrl, payload, Map.class);
        if (resp == null) resp = new HashMap<>();
        return resp;
    }

    public Diet saveDiet(Diet diet) {
        return dietRepository.save(diet);
    }

    /** "여/남" → "female/male" 간단 매핑 */
    private String toGenderEn(String sex) {
        if (sex == null) return "female";
        String s = sex.trim().toLowerCase();
        if (s.startsWith("m") || s.contains("남")) return "male";
        return "female";
    }

    // ===== 기존 메서드들 유지 =====

    public java.util.List<Diet> findMyDiets(Long memberNum) {
        return dietRepository.findByMember_NumOrderByCreatedAtDesc(memberNum);
    }

    public java.util.List<Diet> findAllByMember(Member member){
        return dietRepository.findAllByMemberOrderByDietIdDesc(member);
    }

    // 오늘 해당 회원의 Diet 객체 가져오기
    public Diet findTodayDiet(Long memberNum, LocalDate date) {
        return dietRepository.findByMember_NumAndDietDate(memberNum, date)
                .orElse(null); // 없으면 null
    }
}
