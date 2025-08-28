package com.example.demo.Food.model.dto;


import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FoodResponseDto {
    private String name;
    private Integer confidenceScore;
    private String servingSize;
    private Integer calories;
    private Integer carbohydrates;
    private Integer protein;
    private Integer fat;
    private String analysisDetails;
    private String imageUrl;
}
