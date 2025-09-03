package com.example.demo.food.model;

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
    private Long Id;

    //음식 이름
    private String foodName;

    //음식 칼로리
    private Integer foodCalories;
    //음식 탄수화물
    private Integer foodCarbohydrates;
    //음식 단백질
    private Integer foodProtein;
    //음식 지방
    private Integer foodFat;
    //음식에 대한 설명
    private String foodDescription;

    //업로드하면 저장되는 경로
    private String imagePath;
}
