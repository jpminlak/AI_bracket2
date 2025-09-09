package com.example.demo.member;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.Page;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.web.authentication.logout.SecurityContextLogoutHandler;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
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
    private final AuthenticationManager authenticationManager;

    @GetMapping("/login")
    public String login(@RequestParam(value = "needLogin", required = false) String needLogin, Model model) {
        if ("true".equals(needLogin)) {
            //model.addAttribute("loginMessage", "로그인을 하셔야 서비스를 이용하실 수 있습니다.");
        }
        return "/member/login";
    }

    @GetMapping("/mypage")
    public String mypage(Principal principal, Model model, RedirectAttributes redirectAttributes) {
        return "/member/mypage";
    }

    @GetMapping("/list")
    public String list(Model model,
                       @RequestParam(value = "page", defaultValue = "0") int page) {
        Page<Member> paging = memberService.getList(page, 10);  // 한 페이지에 10명씩
        model.addAttribute("paging", paging);
        return "/member/member_list";
    }

    @GetMapping("/signup")
    public String signup(MemberCreateForm memberCreateForm) {
        return "/member/signup";
    }

    @PostMapping("/signup")
    public String signup(@Valid MemberCreateForm memberCreateForm, BindingResult bindingResult, HttpSession session) {
        if (bindingResult.hasErrors()) {
            return "/member/signup";
        }
        if (!memberCreateForm.getPassword1().equals(memberCreateForm.getPassword2())) {
            bindingResult.rejectValue("password2", "passwordInCorrect", "2개의 패스워드가 일치하지 않습니다.");
            return "/member/signup";
        }

        try {
            memberService.create(memberCreateForm);

            // 회원가입 성공 후 자동 로그인 처리
            UsernamePasswordAuthenticationToken authToken = new UsernamePasswordAuthenticationToken(memberCreateForm.getMemberId(), memberCreateForm.getPassword1());
            Authentication authentication = authenticationManager.authenticate(authToken);
            SecurityContextHolder.getContext().setAuthentication(authentication);

            // 세션에 인증 정보 저장
            session.setAttribute(HttpSessionSecurityContextRepository.SPRING_SECURITY_CONTEXT_KEY, SecurityContextHolder.getContext());

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
            memberModifyForm.setMemberName(member.getMemberName());
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
    public String modify(@Valid @ModelAttribute("memberModifyForm") MemberModifyForm memberModifyForm,
                         BindingResult bindingResult, Principal principal) {
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
            memberSecurityService.updateAuthentication(updatedMember);  // 수정된 정보로 세션 갱신
        } catch (Exception e) {
            bindingResult.reject("modifyFailed", e.getMessage());
            return "/member/modify";
        }
        return "redirect:/member/mypage";
    }

    @GetMapping("/withdrawal")
    public String showWithdrawalForm(Principal principal) {
        if (principal == null) {
            return "redirect:/member/login";
        }
        return "/member/withdrawal";
    }

    @PostMapping("/withdrawal")
    public String withdrawMember(@AuthenticationPrincipal User user,
                                 HttpServletRequest request,
                                 HttpServletResponse response,
                                 RedirectAttributes redirectAttributes) {

        // 현재 로그인된 사용자의 ID를 가져옴
        String memberId = user.getUsername();

        try {
            // MemberService의 회원 탈퇴 메서드 호출
            memberService.withdraw(memberId);

            // 회원 탈퇴 성공 시 스프링 시큐리티 로그아웃 처리
            // SecurityContextLogoutHandler를 사용하여 세션을 무효화하고 인증 정보를 삭제합니다.
            new SecurityContextLogoutHandler().logout(request, response, null);

            // 성공 메시지를 추가하고 bye 페이지로 리다이렉트
            redirectAttributes.addFlashAttribute("message", "회원 탈퇴가 완료되었습니다.");
            return "redirect:/member/bye";

        } catch (Exception e) {
            // 예외 발생 시 오류 메시지를 추가하고 회원 탈퇴 페이지로 돌아감
            redirectAttributes.addFlashAttribute("errorMessage", "회원 탈퇴 중 오류가 발생했습니다.");
            return "redirect:/member/withdrawal";
        }
    }

    @GetMapping("/bye")
    public String showByePage() {
        return "/member/bye";
    }
}