package com.example.demo;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.security.servlet.PathRequest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.DisabledException;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationFailureHandler;

import java.io.IOException;

@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .authorizeHttpRequests((authorizeHttpRequests) -> authorizeHttpRequests
                        //.requestMatchers(PathRequest.toStaticResources().atCommonLocations()).permitAll()   // 가장 먼저 정적 리소스에 대한 접근을 모두 허용
                        .requestMatchers("/css/**", "/js/**", "/images/**").permitAll() // 가장 먼저 정적 리소스(CSS, JS, 이미지 등)도 모든 사용자가 접근 가능하도록 설정
                        .requestMatchers("/main.css").permitAll()
                        .requestMatchers("/member/login", "/member/signup", "/terms", "/notice", "/").permitAll()  // 로그아웃 상태에서도 접근 가능한 경로들
                        .anyRequest().authenticated())  // 위에 명시된 경로를 제외한 모든 경로는 인증된 사용자(로그인한 사용자)만 접근 가능
                .formLogin((formLogin) -> formLogin
                        .loginPage("/member/login")
                        .failureHandler(authenticationFailureHandler())
                        .usernameParameter("memberId")  // 필드 이름을 직접 지정. 이게 없으면 Security는 기본적으로 username으로 ID를 찾음.
                        .defaultSuccessUrl("/"))
                .logout((logout) -> logout
                        .logoutUrl("/member/logout") // logoutRequestMatcher 대신 logoutUrl을 사용합니다.
                        .logoutSuccessUrl("/")
                        .invalidateHttpSession(true))
                .exceptionHandling((exceptionHandling) -> exceptionHandling
                        // 인증되지 않은 사용자가 보호된 리소스에 접근할 때 처리
                        .authenticationEntryPoint((request, response, authException) -> {
                            response.sendRedirect("/member/login?auth_error");
                        }));
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    AuthenticationManager authenticationManager(AuthenticationConfiguration authenticationConfiguration) throws Exception {
        return authenticationConfiguration.getAuthenticationManager();
    }

    @Bean
    public AuthenticationFailureHandler authenticationFailureHandler() {
        return new AuthenticationFailureHandler() {
            @Override
            public void onAuthenticationFailure(HttpServletRequest request,
                                                HttpServletResponse response,
                                                AuthenticationException exception)
                    throws IOException, ServletException {
                System.out.println("로그인 실패 예외 타입: " + exception.getClass().getName());
                if (exception instanceof DisabledException
                        || exception.getCause() instanceof DisabledException) {
                    response.sendRedirect("/member/login?error=withdrawal");
                } else {
                    response.sendRedirect("/member/login?error=bad");
                }
            }
        };
    }
}

