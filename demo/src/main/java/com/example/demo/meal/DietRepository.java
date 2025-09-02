package com.example.demo.meal;

import com.example.demo.member.Member;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DietRepository extends JpaRepository<Diet, Long> {
    //List<Diet> findByMember_IdOrderByCreatedAtDesc(Long memberId);
    List<Diet> findByMember_NumOrderByCreatedAtDesc(Long num);
    List<Diet> findAllByMemberOrderByDietIdDesc(Member member);
}
