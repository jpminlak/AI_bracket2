package com.example.demo.Meal;

import com.example.demo.member.Member;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DietRepository extends JpaRepository<Diet, Long> {
    List<Diet> findByMember_IdOrderByCreatedAtDesc(Long memberId);
    List<Diet> findAllByMemberOrderByDietIdDesc(Member member);
}
