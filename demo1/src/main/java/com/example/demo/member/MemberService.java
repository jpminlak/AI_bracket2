package com.example.demo.member;

import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import java.time.LocalDate;

@RequiredArgsConstructor
@Service
public class MemberService {

    private final MemberRepository memberRepository;
    private final PasswordEncoder passwordEncoder;

    public Member create(MemberCreateForm memberCreateForm) {
        Member member = new Member();
        member.setMemberId(memberCreateForm.getMemberId());
        member.setUsername(memberCreateForm.getUsername());
        member.setPassword(passwordEncoder.encode(memberCreateForm.getPassword1()));
        member.setSex(memberCreateForm.getSex());
        member.setBirthday(memberCreateForm.getBirthday());
        member.setHeight(memberCreateForm.getHeight());
        member.setWeight(memberCreateForm.getWeight());
        member.setEmail(memberCreateForm.getEmail());
        member.setTel(memberCreateForm.getTel());
        member.setRegDate(LocalDate.now()); // regDate 필드 추가
        this.memberRepository.save(member);
        return member;
    }
}
