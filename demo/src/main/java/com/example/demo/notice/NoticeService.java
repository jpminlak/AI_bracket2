package com.example.demo.notice;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class NoticeService {
    private final NoticeRepository noticeRepository;

    public List<Notice> getNoticeList() {
        return noticeRepository.findAll();
    }

    // 이 부분이 새로 추가된 공지사항 저장 메서드입니다.
    public void saveNotice(String noticeTitle, String noticeContent) {
        Notice newNotice = Notice.builder()
                .noticeTitle(noticeTitle)
                .noticeContent(noticeContent)
                .regDate(LocalDateTime.now())
                .build();
        noticeRepository.save(newNotice);
    }
}