package com.example.demo.member;

import jakarta.persistence.Column;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

@Getter
@Setter
public class MemberCreateForm {
    @Size(min = 3, max = 20)
    @NotEmpty(message = "사용자 ID는 필수항목입니다.")
    private String memberId;

    @NotEmpty(message = "이름은 필수항목입니다.")
    private String username;

    @NotEmpty(message = "비밀번호는 필수항목입니다.")
    private String password1;

    @NotEmpty(message = "비밀번호 확인은 필수항목입니다.")
    private String password2;

    @NotEmpty(message = "성별은 필수항목입니다.")
    private String sex;

    @NotNull(message = "생년월일은 필수항목입니다.")
    private LocalDate birthday;

    @NotNull(message = "신장은 필수항목입니다.")
    private Integer height;

    @NotNull(message = "체중은 필수항목입니다.")
    private Integer weight;

    @Email
    private String email;

    private String tel;
}