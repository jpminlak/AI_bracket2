package com.example.demo.member;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

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

    private LocalDate regDate;
    private LocalDate uptDate;
}
