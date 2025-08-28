package com.example.demo.member;

import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

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

    @Transactional
    public void withdraw(String memberId) {
        // 1. 회원 존재 여부 확인
        Optional<Member> memberOptional = memberRepository.findByMemberId(memberId);
        if (memberOptional.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "해당 회원을 찾을 수 없습니다.");
        }
        Member member = memberOptional.get();

        // 2. 회원의 상태를 WITHDRAWAL로 변경
        member.setStatus(MemberStatus.WITHDRAWAL);
        memberRepository.save(member); // 변경된 상태를 저장

        // 3. (선택 사항) 관련 데이터 처리
        // 예를 들어, 게시물 등을 비공개로 전환하는 로직을 추가할 수 있습니다.
        // postService.setPrivateByMemberId(memberId);
    }

    // 회원 가입 메서드. 이미 존재하는 ID가 탈퇴 상태인 경우에도 가입을 막음.
    public void signup(MemberCreateForm memberCreateForm) {
        // 1. 회원 ID 중복 검사
        Optional<Member> existingMember = memberRepository.findByMemberId(memberCreateForm.getMemberId());

        if (existingMember.isPresent()) {
            // 이미 존재하는 계정이 활성화 상태라면 예외 발생
            if (existingMember.get().getStatus() == MemberStatus.ACTIVE) {
                throw new IllegalStateException("이미 사용 중인 아이디입니다.");
            }
            // 이미 존재하는 계정이 탈퇴 상태라면 재가입 불가 처리
            if (existingMember.get().getStatus() == MemberStatus.WITHDRAWAL) {
                throw new IllegalStateException("탈퇴한 계정으로는 재가입할 수 없습니다.");
            }
        }
    }
}
