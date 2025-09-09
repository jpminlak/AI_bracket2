package com.example.demo.inquiry;

import com.example.demo.member.Member;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Getter
@Setter
public class Inquiry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "member_num")
    private Member member;

    private String subject;

    @Column(columnDefinition = "TEXT")
    private String message;

    private LocalDateTime regDate;

    private boolean answered;

    @Column(columnDefinition = "TEXT")
    private String replyMessage;

    private LocalDateTime repliedAt;
}