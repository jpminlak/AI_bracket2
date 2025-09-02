package com.example.demo.meal;

import com.example.demo.member.Member;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RequiredArgsConstructor
@Service
public class DietService {

    @Value("${diet.api-base:http://127.0.0.1:8001}")
    private String apiBase;

    private final DietRepository dietRepository;
    private final RestTemplate restTemplate = new RestTemplate();

    /** "여/남" → "female/male" */
    private String toGenderEn(String sex) {
        if (sex == null) return "female";
        String s = sex.trim();
        if (s.equals("남") || s.equalsIgnoreCase("m") || s.startsWith("남")) return "male";
        return "female";
    }

    /** FastAPI 호출: 성별/키/몸무게만 사용 (age/activity는 기본값으로 채워 전송) */
    public Map<String, Object> recommend(String sex, Double height, Double weight) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("gender", toGenderEn(sex));
        payload.put("height_cm", height);
        payload.put("weight_kg", weight);
        // 구조는 그대로 두되, 서버가 필요로 할 수 있는 기본값을 안전하게 채움
        payload.put("age", 21);
        payload.put("activity_level", "light");

        String url = apiBase + "/recommend?live=true";
        Map<String, Object> res = restTemplate.postForObject(url, payload, Map.class);
        return res != null ? res : Map.of();
    }

    /** 추천 결과(Map)를 DB에 저장 (메뉴 문자열과 total_kcal만 저장) */
    public Diet saveFromResult(Member member, Map<String, Object> r) {
        Map<String, Object> b = (Map<String, Object>) r.getOrDefault("breakfast", Map.of());
        Map<String, Object> l = (Map<String, Object>) r.getOrDefault("lunch", Map.of());
        Map<String, Object> d = (Map<String, Object>) r.getOrDefault("dinner", Map.of());

        String breakfast = String.valueOf(b.getOrDefault("menu", ""));
        String lunch = String.valueOf(l.getOrDefault("menu", ""));
        String dinner = String.valueOf(d.getOrDefault("menu", ""));
        Integer total = toInt(r.get("total_kcal"), 0);

        Diet diet = new Diet();
        diet.setMember(member);
        diet.setBreakfast(breakfast);
        diet.setLunch(lunch);
        diet.setDinner(dinner);
        diet.setTotalKcal(total);

        return dietRepository.save(diet);
    }

    private Integer toInt(Object o, int def) {
        try {
            if (o == null) return def;
            return (int) Math.round(Double.parseDouble(o.toString()));
        } catch (Exception e) {
            return def;
        }
    }

    public List<Diet> findMyDiets(Long memberNum) {
        return dietRepository.findByMember_NumOrderByCreatedAtDesc(memberNum);
    }

    public List<Diet> findAllByMember(Member member){
        return dietRepository.findAllByMemberOrderByDietIdDesc(member);
    }
}