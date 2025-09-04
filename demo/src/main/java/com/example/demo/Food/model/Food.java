package com.example.demo.Food.model;

import com.example.demo.member.Member;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;


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


    @Column(name = "image_data")
    @Lob
    private byte[] imageData;

    // 식사 시간 (아침/점심/저녁/없음)
    @Column(name = "meal_time")
    private String mealTime;

    @CreationTimestamp
    @Column(name = "reg_date", nullable = false, updatable = false, columnDefinition = "DATETIME")
    private LocalDateTime regDate;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "member_num") // food 테이블에 member 외래키 생성
    private Member member;
}

