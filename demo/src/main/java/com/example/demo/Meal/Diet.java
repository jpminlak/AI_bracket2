package com.example.demo.Meal;

import com.example.demo.member.Member;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Entity
public class Diet {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "diet_id")   // DB 컬럼은 그대로 diet_id 사용
    private Long dietId;        // ✅ 프로퍼티명은 dietId

    @Lob
    @Column
    private String breakfast;

    @Lob
    @Column
    private String lunch;

    @Lob
    @Column
    private String dinner;

    @Column
    private double total_calories;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_id", nullable = true) // 기존 데이터가 있을 수 있어 우선 nullable 허용
    private Member member;
}
