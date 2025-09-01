package com.example.demo.Meal;

import com.example.demo.member.Member;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class DietService {

    private final DietRepository dietRepository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // (추가)
    public List<Diet> findAllDesc() {
        return dietRepository.findAllByOrderByDietIdDesc();
    }

    /** 로그인 회원별 목록 */
    public List<Diet> findAllByMember(Member member) {
        if (member == null) return Collections.emptyList();
        return dietRepository.findAllByMemberOrderByDietIdDesc(member);
    }

    /** FastAPI 응답 Map -> Diet 저장 (회원 연결) */
    public Diet saveFromApiMap(Map<String, Object> r, Member member) {
        Diet d = new Diet();
        d.setBreakfast(toJson(r.get("breakfast")));
        d.setLunch(toJson(r.get("lunch")));
        d.setDinner(toJson(r.get("dinner")));
        Object total = r.get("total_kcal");
        d.setTotal_calories(total != null ? safeDouble(total) : 0.0);
        d.setMember(member); // ✅ 핵심: 로그인 사용자 연결
        return dietRepository.save(d);
    }

    private String toJson(Object v) {
        try { return objectMapper.writeValueAsString(v); }
        catch (Exception e) { return String.valueOf(v); }
    }

    private double safeDouble(Object v) {
        try { return Double.parseDouble(String.valueOf(v)); }
        catch (Exception e) { return 0.0; }
    }
}
