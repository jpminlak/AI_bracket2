package com.example.demo.notice;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class NoticeService {
    private final NoticeRepository noticeRepository;

    public Page<Notice> getNoticeList(Pageable pageable) {
        return noticeRepository.findAll(pageable);
    }

    public void saveNotice(String noticeTitle, String noticeContent) {
        Notice newNotice = Notice.builder()
                .noticeTitle(noticeTitle)
                .noticeContent(noticeContent)
                .regDate(LocalDateTime.now())
                .build();
        noticeRepository.save(newNotice);
    }

    public Notice findById(Integer  id) {
        return noticeRepository.findById(id).orElse(null);
    }
}