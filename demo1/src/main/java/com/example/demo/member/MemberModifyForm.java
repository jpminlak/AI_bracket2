package com.example.demo.member;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.Setter;
import org.springframework.format.annotation.DateTimeFormat;

import java.time.LocalDate;

@Getter
@Setter
public class MemberModifyForm {

    // 수정할 수 없는 필드는 validation을 제거하거나, 입력 폼에서 readonly로 설정
    @Size(min = 3, max = 20)
    private String memberId; // ID는 수정하지 않는 것이 일반적입니다.

    @NotEmpty(message = "이름은 필수항목입니다.")
    private String username;

    @NotEmpty(message = "비밀번호는 필수항목입니다.")
    private String password1;

    @NotEmpty(message = "비밀번호 확인은 필수항목입니다.")
    private String password2;

    @NotEmpty(message = "성별은 필수항목입니다.")
    private String sex;

    @NotNull(message = "생년월일은 필수항목입니다.")
    @DateTimeFormat(pattern = "yyyy-MM-dd")
    private LocalDate birthday;

    @NotNull(message = "신장은 필수항목입니다.")
    private Integer height;

    @NotNull(message = "체중은 필수항목입니다.")
    private Integer weight;

    @Email(message = "이메일 형식이 올바르지 않습니다.")
    private String email;

    private String tel;
}