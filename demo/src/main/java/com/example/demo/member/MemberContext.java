package com.example.demo.member;

import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.User;

import java.util.Collection;

public class MemberContext extends User {
    private final Member member;

    public MemberContext(Member member, Collection<? extends GrantedAuthority> authorities) {
        super(member.getMemberId(), member.getPassword(), authorities);
        this.member = member;
    }

    public Member getMember() {
        return member;
    }

    public boolean isEnabled() {
        // status가 NULL이면 정상 회원으로 간주
        return member.getStatus() == null || member.getStatus() == MemberStatus.ACTIVE;
    }
}