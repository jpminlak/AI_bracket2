package com.example.demo.member;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Optional;

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
        member.setRegDate(LocalDateTime.now()); // regDate 필드 추가
        this.memberRepository.save(member);
        return member;
    }

    // 회원정보 조회 메서드
    public Member getMember(String memberId) {
        Optional<Member> memberOptional = this.memberRepository.findByMemberId(memberId);
        if (memberOptional.isPresent()) {
            return memberOptional.get();
        } else {
            // 사용자를 찾을 수 없을 경우 예외 발생
            throw new IllegalArgumentException("User not found");
        }
    }

    // 회원정보 수정 메서드
    @Transactional
    public Member modify(String memberId, MemberModifyForm memberModifyForm) {
        Member member = memberRepository.findByMemberId(memberId)
                .orElseThrow(() -> new RuntimeException("회원 없음"));

        // DTO의 값으로 엔티티를 업데이트
        member.setUsername(memberModifyForm.getUsername());
        member.setPassword(passwordEncoder.encode(memberModifyForm.getPassword1()));
        member.setSex(memberModifyForm.getSex());
        member.setBirthday(memberModifyForm.getBirthday());
        member.setHeight(memberModifyForm.getHeight());
        member.setWeight(memberModifyForm.getWeight());
        member.setEmail(memberModifyForm.getEmail());
        member.setTel(memberModifyForm.getTel());
        member.setUptDate(LocalDateTime.now()); // 최종 수정일 업데이트
        memberRepository.save(member);
        return member;
    }
}
