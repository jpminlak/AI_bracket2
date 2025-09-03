package com.example.demo.meal;

import com.example.demo.member.Member;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity @Getter @Setter
@Table(name = "diet")
public class Diet {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name="diet_id")
    private Long dietId;

    @ManyToOne(optional = false, fetch = FetchType.LAZY)
    @JoinColumn(name = "member_num")
    private Member member;

    @Column(nullable = false, length = 500)
    private String breakfast;

    @Column(nullable = false, length = 500)
    private String lunch;

    @Column(nullable = false, length = 500)
    private String dinner;

    @Column(name = "total_calories")
    private double totalKcal;

    @Column(nullable = false)
    private LocalDate dietDate = LocalDate.now();

    @CreationTimestamp
    private LocalDateTime createdAt;
}