package com.example.demo.Food.controller;


import com.example.demo.Food.model.dto.FoodResponseDto;
import com.example.demo.Food.Service.FoodService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/food")
@RequiredArgsConstructor
public class FoodController {

    private final FoodService foodService;

    @PostMapping("/upload")
    public ResponseEntity<FoodResponseDto> uploadFoodImage(@RequestPart("foodFile") MultipartFile file) throws Exception {
        FoodResponseDto response = foodService.analyzeFood(file);
        return ResponseEntity.ok(response);
    }
}