package com.example.demo.meal;

import com.example.demo.member.Member;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface DietRepository extends JpaRepository<Diet, Long> {
    //List<Diet> findByMember_IdOrderByCreatedAtDesc(Long memberId);
    List<Diet> findByMember_NumOrderByCreatedAtDesc(Long num);
    List<Diet> findAllByMemberOrderByDietIdDesc(Member member);
    Optional<Diet> findByMember_NumAndDietDate(Long memberNum, LocalDate dietDate);
}