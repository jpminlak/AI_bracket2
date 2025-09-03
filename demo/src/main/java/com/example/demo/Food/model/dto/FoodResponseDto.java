package com.example.demo.Food.model.dto;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Getter
@Setter
public class FoodResponseDto {
    private String name;             // 음식 이름
    private Integer confidenceScore; // 신뢰도 (%)
    private Double calories;
    private Double protein;
    private Double fat;
    private Double carbohydrates;
    private String analysisDetails;  // 분석 상세 (출처 표시 등)
}
