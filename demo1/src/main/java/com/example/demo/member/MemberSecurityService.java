package com.example.demo.member;

import lombok.RequiredArgsConstructor;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@RequiredArgsConstructor
@Service
public class MemberSecurityService implements UserDetailsService {

    private final MemberRepository memberRepository;

    @Override
    public UserDetails loadUserByUsername(String memberId) throws UsernameNotFoundException {
        Optional<Member> _member = this.memberRepository.findByMemberId(memberId);
        if (_member.isEmpty()) {
            throw new UsernameNotFoundException("사용자를 찾을수 없습니다.");
        }
        Member member = _member.get();
        List<GrantedAuthority> authorities = new ArrayList<>();
        if ("admin".equals(memberId)) {
            authorities.add(new SimpleGrantedAuthority(MemberRole.ADMIN.getValue()));
        } else {
            authorities.add(new SimpleGrantedAuthority(MemberRole.USER.getValue()));
        }
        return new MemberContext(member, authorities);
        //return new User(member.getMemberId(), member.getPassword(), authorities);


        // User 객체의 첫 번째 인자는 Spring Security가 인증에 사용하는 'username'입니다.
        // 두 번째 인자는 패스워드입니다.
        // 여기서는 User 객체의 'username'에 DB의 'memberId'를 사용하고,
        // 실제 사용자 이름은 별도로 관리하는 것이 일반적입니다.
        // 하지만 간편하게 실제 사용자 이름을 직접 사용하도록 수정할 수 있습니다.

        // 이 방식이 더 간단합니다.
        //return new User(member.getUsername(), member.getPassword(), authorities);
    }
}
