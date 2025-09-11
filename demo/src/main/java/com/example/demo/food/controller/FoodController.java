package com.example.demo.food.controller;

import com.example.demo.food.Repository.FoodRepository;
import com.example.demo.food.model.Food;
import com.example.demo.food.model.dto.FoodResponseDto;
import com.example.demo.food.Service.FoodService;
import com.example.demo.member.Member;
import com.example.demo.member.MemberService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.Optional;

@Controller
@RequestMapping("/photo")
@RequiredArgsConstructor
public class FoodController {

    private final FoodService foodService;
    private final FoodRepository foodRepository;
    private final MemberService memberService;

    @GetMapping
    public String uploadPhotoPage() {
        return "/photo/analyse";
    }

    @PostMapping("/upload")
    @ResponseBody
    public ResponseEntity<FoodResponseDto> uploadFood(@RequestPart("foodFile") MultipartFile file) {
        try {
            return ResponseEntity.ok(foodService.analyzeFood(file));
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                    .body(FoodResponseDto.builder()
                            .analysisDetails("이미지 분석 실패: " + e.getMessage())
                            .build());
        }
    }

    @PostMapping("/save")
    @ResponseBody
    public Food saveFood(@RequestBody Food food, Authentication auth) {
        // 로그인 사용자 가져오기
        Member me = resolveCurrentMember(auth);
        food.setMember(me); // ⭐ member 반드시 세팅
        return foodRepository.save(food);
    }

    private Member resolveCurrentMember(Authentication auth) {
        if (auth == null || auth.getName() == null) {
            throw new IllegalStateException("인증정보 없음");
        }
        String key = auth.getName(); // 로그인 아이디 또는 PK
        Optional<Member> byLoginId = memberService.findByMemberId(key);
        if (byLoginId.isPresent()) return byLoginId.get();
        try {
            Long id = Long.valueOf(key);
            Optional<Member> byId = memberService.findByNum(id);
            if (byId.isPresent()) return byId.get();
        } catch (NumberFormatException ignore) {}
        throw new IllegalStateException("회원 없음");
    }
}