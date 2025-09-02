package com.example.demo.Meal.controller;


import com.example.demo.Meal.Diet;
import com.example.demo.Meal.DietService;
import com.example.demo.member.Member;
import com.example.demo.member.MemberService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RequiredArgsConstructor
@Controller
public class DietController {

    private final DietService dietService;
    private final MemberService memberService;

    /** 식단추천 폼 */
    @GetMapping("/diet")
    public String dietForm(Model model, Authentication auth) {
        model.addAttribute("today", LocalDate.now());
        return "meal/diet"; // diet.html
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
        model.addAttribute("r", r); // result.html은 Map r을 사용
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

        // result.html로부터 넘어온 값으로 저장
        Map<String, Object> r = Map.of(
                "breakfast", Map.of("menu", breakfast),
                "lunch",     Map.of("menu", lunch),
                "dinner",    Map.of("menu", dinner),
                "total_kcal", totalKcal
        );
        dietService.saveFromResult(me, r);
        return "redirect:/record";
    }

    @GetMapping("record")
    public  String record(Authentication auth, Model model) {
        Member me = resolveCurrentMember(auth);
        List<Diet> diets = dietService.findMyDiets(me.getId());
        model.addAttribute("diets", diets);
        return "meal/record";
    }

    private Member resolveCurrentMember(Authentication auth){
        if (auth == null || auth.getName() == null) {
            throw  new IllegalStateException("인증정보 없음");
        }
        String key = auth.getName(); // 보통 로그인 아이디(memberId) 또는 문자열된 PK
        Optional<Member> byLoginId = memberService.findByMemberId(key);
        if(byLoginId.isPresent()) return byLoginId.get();
        try {
            Long id = Long.valueOf(key);
            Optional<Member> byId = memberService.findById(id);
            if (byId.isPresent()) return byId.get();
        }catch (NumberFormatException ignore) { /* key가 숫자가 아닐 수 있음 */ }
            throw new IllegalStateException("회원 없음");

    }

}
