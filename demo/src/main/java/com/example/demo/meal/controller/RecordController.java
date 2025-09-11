package com.example.demo.meal.controller;

import com.example.demo.meal.AuthUtils;
import com.example.demo.meal.Diet;
import com.example.demo.meal.DietService;
import com.example.demo.member.Member;
import com.example.demo.member.MemberService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RequiredArgsConstructor
@RequestMapping("/record")
@Controller
public class RecordController {
    private final DietService dietService;
    private final MemberService memberService;

    @GetMapping("/calendar")
    public String calendar(
            Authentication auth,
            Model model,
            @RequestParam(required = false) Integer year,
            @RequestParam(required = false) Integer month,
            @RequestParam(defaultValue = "0") int page,   // 0부터 시작
            @RequestParam(defaultValue = "10") int size
    ) {
        Member me = AuthUtils.resolveCurrentMember(auth, memberService);
        if (year == null || month == null) {
            LocalDate now = LocalDate.now();
            year = now.getYear();
            month = now.getMonthValue();
        }
        List<Diet> allDiets = dietService.findAllByMember(me);

        int fromIndex = page * size;
        int toIndex = Math.min(fromIndex + size, allDiets.size());
        List<Diet> diets = allDiets.subList(fromIndex, toIndex);

        Map<LocalDate, Double> summary = new HashMap<>();
        for (Diet d : allDiets) { // 캘린더는 전체 summary 필요
            summary.put(d.getDietDate(), d.getTotalKcal());
        }

        int totalPages = (int) Math.ceil((double) allDiets.size() / size);

        model.addAttribute("summary", summary);
        model.addAttribute("diets", diets);
        model.addAttribute("year", year);
        model.addAttribute("month", month);
        model.addAttribute("page", page);
        model.addAttribute("totalPages", totalPages);
        model.addAttribute("size", size);

        return "meal/calendar";
    }

    // 특정 날짜 상세보기
    @GetMapping("/{date}")
    public String recordByDate(@PathVariable String date, Authentication auth, Model model) {
        Member me = AuthUtils.resolveCurrentMember(auth, memberService);
        //Member me = resolveCurrentMember(auth);
        LocalDate target = LocalDate.parse(date);
        Diet diet = dietService.findTodayDiet(me.getNum(), target);
        model.addAttribute("d", diet);
        model.addAttribute("date", target); // 화면에 표시할 날짜
        return "meal/record";
    }

//    private Member resolveCurrentMember(Authentication auth){
//        if (auth == null || auth.getName() == null) {
//            throw new IllegalStateException("인증정보 없음");
//        }
//        String key = auth.getName();
//        Optional<Member> byLoginId = memberService.findByMemberId(key);
//        if(byLoginId.isPresent()) return byLoginId.get();
//        try {
//            Long id = Long.valueOf(key);
//            Optional<Member> byId = memberService.findByNum(id);
//            if (byId.isPresent()) return byId.get();
//        } catch (NumberFormatException ignore) { }
//        throw new IllegalStateException("회원 없음");
//    }
}