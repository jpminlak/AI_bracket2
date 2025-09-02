package com.example.demo.food.controller;

import com.example.demo.food.model.dto.FoodResponseDto;
import com.example.demo.food.Service.FoodService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@Controller     // @Restcontroller를 쓰면 return에 쓴 문장이 그대로 출력된다. 그냥 @Controller를 써야 html 문서 렌더링.
@RequestMapping("/photo")    // URL 단순화
@RequiredArgsConstructor
public class FoodController {

    private final FoodService foodService;

    @GetMapping
    public String uploadPhoto(){
        return "/photo/index";
    }

    @PostMapping("/upload")
    public ResponseEntity<FoodResponseDto> uploadFoodImage(@RequestPart("foodFile") MultipartFile file) throws Exception {
        FoodResponseDto response = foodService.analyzeFood(file);
        return ResponseEntity.ok(response);
    }
}