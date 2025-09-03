package com.example.demo.Food.controller;

import com.example.demo.food.model.dto.FoodResponseDto;
import com.example.demo.Food.Service.FoodService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/photo")
@RequiredArgsConstructor
public class FoodController {

    private final FoodService foodService;

    @GetMapping
    public String status() {
        return "Food API is running";
    }

    @PostMapping("/upload")
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
}
