package com.example.demo.inquiry;

import com.example.demo.member.Member;
import com.example.demo.member.MemberContext;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

@Controller
@RequiredArgsConstructor
@RequestMapping("/inquiry")
public class InquiryController {

    private final InquiryService inquiryService;

    // 사용자 문의 작성 페이지
    @GetMapping
    public String contactForm(@AuthenticationPrincipal MemberContext memberContext, Model model) {
        Member member = memberContext.getMember();
        if (!inquiryService.canContact(member)) {
            model.addAttribute("alertMessage", "등록된 이메일이 없습니다. 회원정보에서 이메일을 입력해주세요.");
            return "redirect:/";  // 이메일 없는 회원은 메인으로
        }
        model.addAttribute("inquiryForm", new InquiryForm());
        return "footer/inquiry_form";
    }

    // 사용자 문의 저장
    @PostMapping
    public String submitContact(@AuthenticationPrincipal MemberContext memberContext,
                                InquiryForm inquiryForm, Model model) {
        Member member = memberContext.getMember();
        if (!inquiryService.canContact(member)) {
            model.addAttribute("alertMessage", "등록된 이메일이 없습니다. 회원정보에서 이메일을 입력해주세요.");
            return "redirect:/";
        }
        inquiryService.saveInquiry(member, inquiryForm.getSubject(), inquiryForm.getMessage());
        model.addAttribute("alertMessage", "문의가 정상적으로 등록되었습니다.");
        return "redirect:/";
    }

    // 관리자 페이지: 문의 목록
    @GetMapping("/list")
    public String inquiries(@RequestParam(defaultValue = "0") int page, Model model) {
        Page<Inquiry> paging = inquiryService.getAllInquiries(PageRequest.of(page, 10));
        model.addAttribute("paging", paging);
        return "footer/inquiry_list";
    }

    // 관리자 답변 폼
    @GetMapping("/reply/{id}")
    public String showInquiryDetail(@PathVariable Long id, Model model) {
        Inquiry inquiry = inquiryService.getInquiryWithMember(id);
        model.addAttribute("inquiry", inquiry);
        return "footer/inquiry_reply";
    }

    // 관리자 답변 제출
    @PostMapping("/reply/{id}")
    public String replyInquiry(@PathVariable Long id, @RequestParam String replyMessage) {
        inquiryService.replyInquiry(id, replyMessage);
        return "redirect:/inquiry/list";
    }
}