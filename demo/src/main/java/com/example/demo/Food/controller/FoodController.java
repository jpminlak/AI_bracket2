package com.example.demo.Food.controller;

import com.example.demo.Food.model.dto.FoodResponseDto;
import com.example.demo.Food.Service.FoodService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Controller
@RequestMapping("/photo")
@RequiredArgsConstructor
public class FoodController {

    private final FoodService foodService;

    @GetMapping
    public String uploadPhotoPage() {
        return "/photo/index"; // templates/photo/index.html 렌더링
    }

    @PostMapping("/upload")
    @ResponseBody
    public ResponseEntity<FoodResponseDto> uploadFood(@RequestPart("foodFile") MultipartFile file) {
        try {
            // 분석 + DB 저장
            FoodResponseDto dto = foodService.analyzeFood(file);
            return ResponseEntity.ok(dto);
        } catch (Exception e) {
            return ResponseEntity.badRequest()
                    .body(FoodResponseDto.builder()
                            .analysisDetails("이미지 분석 실패: " + e.getMessage())
                            .build());
        }
    }
}
