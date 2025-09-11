package com.example.demo.meal;

import com.example.demo.member.Member;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Getter
@Setter
@Table(name = "diet")
public class Diet {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "diet_id")
    private Long dietId;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "member_num")
    private Member member;

    @Column(nullable = false)
    private LocalDate dietDate = LocalDate.now();

    // 식단 - nullable = true, 기본값 null
    @Column(nullable = true, length = 500)
    private String breakfast;

    @Column(nullable = true, length = 500)
    private String lunch;

    @Column(nullable = true, length = 500)
    private String dinner;

    // 끼니별 칼로리 - nullable = true, 기본값 null
    @Column(nullable = true)
    private Double breakfastKcal;

    @Column(nullable = true)
    private Double lunchKcal;

    @Column(nullable = true)
    private Double dinnerKcal;

    @Column(nullable = true)
    private Double breakfastCarbs;

    @Column(nullable = true)
    private Double breakfastProtein;

    @Column(nullable = true)
    private Double breakfastFat;

    @Column(nullable = true)
    private Double lunchCarbs;

    @Column(nullable = true)
    private Double lunchProtein;

    @Column(nullable = true)
    private Double lunchFat;

    @Column(nullable = true)
    private Double dinnerCarbs;

    @Column(nullable = true)
    private Double dinnerProtein;

    @Column(nullable = true)
    private Double dinnerFat;

    // 하루 총 칼로리
    @Column(name = "total_calories", nullable = true, columnDefinition = "DOUBLE DEFAULT NULL")
    private Double totalKcal;

    @CreationTimestamp
    @Column(nullable = true)
    private LocalDateTime createdAt;
}