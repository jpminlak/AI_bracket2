package com.example.demo.meal;

import com.example.demo.member.Member;
import com.example.demo.member.MemberService;
import org.springframework.security.core.Authentication;

import java.util.Optional;

public class AuthUtils {

    public static Member resolveCurrentMember(Authentication auth, MemberService memberService) {
        if (auth == null || auth.getName() == null) {
            throw new IllegalStateException("인증정보 없음");
        }

        String key = auth.getName();

        // 로그인 ID로 조회
        Optional<Member> byLoginId = memberService.findByMemberId(key);
        if (byLoginId.isPresent()) return byLoginId.get();

        // Long ID로 조회 (예: PK 기반 인증일 경우)
        try {
            Long id = Long.valueOf(key);
            Optional<Member> byId = memberService.findByNum(id);
            if (byId.isPresent()) return byId.get();
        } catch (NumberFormatException ignore) { }

        throw new IllegalStateException("회원 없음");
    }
}