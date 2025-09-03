package com.example.demo.Food.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "food")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Food {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 식품명
    @Column(name = "food_name", nullable = false)
    private String foodName;

    // 에너지(kcal)
    @Column(name = "calories")
    private Double calories;

    // 단백질(g)
    @Column(name = "protein")
    private Double protein;

    // 지방(g)
    @Column(name = "fat")
    private Double fat;

    // 탄수화물(g)
    @Column(name = "carbohydrates")
    private Double carbohydrates;

    // 나트륨(mg)
    @Column(name = "sodium")
    private Double sodium;

    // 기타 필요한 필드 추가
    @Column(name = "moisture")
    private Double moisture;

    @Column(name = "dietary_fiber")
    private Double dietaryFiber;
}