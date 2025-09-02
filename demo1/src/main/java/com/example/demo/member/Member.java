package com.example.demo.member;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Getter
@Setter
@Entity
public class Member {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, length = 20)
    private String memberId;

    @Column(length = 50)
    private String username;

    @Column     // length 기본값 255
    private String password;

    @Column(length = 6)
    private String sex;

    private LocalDate birthday;  // LocalDate 권장
    private Integer height;
    private Integer weight;

    @Column(length = 100)
    private String email;

    @Column(length = 20)
    private String tel;

    @Column(columnDefinition = "DATETIME")  // DB에 밀리초까지 저장될 수도 있다. 이럴 때는 수동으로 데이터 유형을 DATETIME 형식으로 바꿔야 시-분-초까지만 저장한다.
    private LocalDateTime regDate;
    private LocalDateTime uptDate;
}
