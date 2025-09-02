package com.example.demo.inquiry;

import com.example.demo.member.Member;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ContactService {

    private final InquiryRepository inquiryRepository;

    // 이메일 존재 여부 확인
    public boolean canContact(Member member) {
        return member.getEmail() != null && !member.getEmail().isEmpty();
    }

    // 사용자 문의 저장
    public void saveInquiry(Member member, String subject, String message) {
        if (member == null) {
            throw new IllegalArgumentException("회원 정보가 필요합니다.");
        }
        Inquiry inquiry = new Inquiry();
        inquiry.setMember(member);
        inquiry.setSubject(subject);
        inquiry.setMessage(message);
        inquiry.setRegDate(LocalDateTime.now());
        inquiry.setAnswered(false);
        inquiryRepository.save(inquiry);
    }

    // 관리자가 답장 작성
    public void replyInquiry(Long inquiryId, String replyMessage) {
        //Inquiry inquiry = inquiryRepository.findById(inquiryId).orElseThrow();
        Inquiry inquiry = inquiryRepository.findByIdWithMember(inquiryId).orElseThrow();
        inquiry.setReplyMessage(replyMessage);
        inquiry.setAnswered(true);
        inquiry.setRepliedAt(LocalDateTime.now());
        inquiryRepository.save(inquiry);

        // 이메일 전송 기능: 실제 SMTP 없어도 시뮬레이션 가능
        System.out.printf("Reply to %s:\n%s\n", inquiry.getMember().getEmail(), replyMessage);

        // 실제 SMTP 사용 시
        // sendEmail(inquiry.getMember().getEmail(), "문의 답변", replyMessage);
    }

    public List<Inquiry> getAllInquiries() {
        return inquiryRepository.findAllWithMember();  // 모든 문의 가져오기
    }

    public Inquiry getInquiryWithMember(Long id) {
        return inquiryRepository.findByIdWithMember(id).orElseThrow();
    }
}