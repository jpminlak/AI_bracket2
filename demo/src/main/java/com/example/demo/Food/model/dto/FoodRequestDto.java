package com.example.demo.food.model.dto;


import lombok.*;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FoodRequestDto {
    private String foodName;
    private Integer classId;
    private Double confidence;
    private String imagePath;
}
