package com.example.demo.member;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.validation.BindingResult;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.security.Principal;
import java.time.LocalDate;

@RequiredArgsConstructor
@Controller
@RequestMapping("/member")
public class MemberController {

    private final MemberService memberService;
    private final MemberSecurityService memberSecurityService;

    @GetMapping("/login")
    public String login(@RequestParam(value = "needLogin", required = false) String needLogin, Model model) {
        if ("true".equals(needLogin)) {
            model.addAttribute("loginMessage", "로그인을 하셔야 회원정보를 볼 수 있습니다.");
        }
        return "/member/login";
    }

    @GetMapping("/mypage")
    public String mypage(Principal principal, Model model, RedirectAttributes redirectAttributes) {
        if (principal == null) {
            // RedirectAttributes를 사용하여 메시지를 flash 속성으로 전달
            redirectAttributes.addFlashAttribute("loginMessage", "로그인을 하셔야 회원정보를 볼 수 있습니다.");
            return "redirect:/member/login";
        }
        return "/member/mypage";
    }

    @GetMapping("/signup")
    public String signup(MemberCreateForm memberCreateForm) {
        return "/member/signup";
    }

    @PostMapping("/signup")
    public String signup(@Valid MemberCreateForm memberCreateForm, BindingResult bindingResult) {
        if (bindingResult.hasErrors()) {
            return "/member/signup";
        }
        if (!memberCreateForm.getPassword1().equals(memberCreateForm.getPassword2())) {
            bindingResult.rejectValue("password2", "passwordInCorrect",
                    "2개의 패스워드가 일치하지 않습니다.");
            return "/member/signup";
        }

        try {
            memberService.create(memberCreateForm);
            return "redirect:/";
        } catch(DataIntegrityViolationException e) {
            e.printStackTrace();
            bindingResult.reject("signupFailed", "이미 등록된 사용자입니다.");
            return "/member/signup";
        } catch(Exception e) {
            e.printStackTrace();
            bindingResult.reject("signupFailed", e.getMessage());
            return "/member/signup";
        }
    }

    @GetMapping("/modify")
    public String modify(Principal principal, Model model) {
        if (principal == null) {
            return "redirect:/member/login";
        }

        // 폼 객체가 모델에 이미 있는지 확인
        if (!model.containsAttribute("memberModifyForm")) {
            String memberId = principal.getName();
            Member member = memberService.getMember(memberId);

            MemberModifyForm memberModifyForm = new MemberModifyForm();
            memberModifyForm.setMemberId(member.getMemberId());
            memberModifyForm.setUsername(member.getUsername());
            memberModifyForm.setEmail(member.getEmail());
            memberModifyForm.setTel(member.getTel());
            memberModifyForm.setBirthday(member.getBirthday());
            memberModifyForm.setSex(member.getSex());
            memberModifyForm.setHeight(member.getHeight());
            memberModifyForm.setWeight(member.getWeight());

            model.addAttribute("memberModifyForm", memberModifyForm);
        }

        return "/member/modify";
    }

    @PostMapping("/modify")
    public String modify(
            @Valid @ModelAttribute("memberModifyForm") MemberModifyForm memberModifyForm,
            BindingResult bindingResult,
            Principal principal) {

        if (bindingResult.hasErrors()) {
            return "/member/modify";
        }

        if (!memberModifyForm.getPassword1().equals(memberModifyForm.getPassword2())) {
            bindingResult.rejectValue("password2", "passwordInCorrect",
                    "2개의 패스워드가 일치하지 않습니다.");
            return "/member/modify";
        }

        String currentMemberId = principal.getName();
        try {
            Member updatedMember = memberService.modify(currentMemberId, memberModifyForm);

            // ✅ 수정된 정보로 세션 갱신
            memberSecurityService.updateAuthentication(updatedMember);

        } catch (Exception e) {
            bindingResult.reject("modifyFailed", e.getMessage());
            return "/member/modify";
        }

        return "redirect:/member/mypage";
    }
}