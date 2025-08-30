package com.example.demo.notice;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
@RequiredArgsConstructor
public class NoticeController {
    private final NoticeService noticeService;

    @GetMapping("/notice")
    public String notice(Model model) {
        var noticeList = noticeService.getNoticeList();
        model.addAttribute("noticeList", noticeList);
        return "footer/notice";
    }

    @GetMapping("/notice_write")
    public String notice_write(Model model) {
        return "footer/notice_write";
    }

    @PostMapping("/notice_write")
    public String writeNotice(@RequestParam("noticeTitle") String noticeTitle,
                              @RequestParam("noticeContent") String noticeContent) {

        // NoticeService를 사용하여 제목과 내용을 저장하는 로직을 호출합니다.
        // 예를 들어, noticeService.saveNotice(noticeTitle, noticeContent); 와 같이 구현할 수 있습니다.
        // 현재 코드에는 이 메서드가 없으므로, NoticeService에 saveNotice 메서드를 추가해야 합니다.
        noticeService.saveNotice(noticeTitle, noticeContent);

        // 글쓰기 성공 후, 공지사항 목록 페이지로 리다이렉트합니다.
        return "redirect:/notice";
    }
}
