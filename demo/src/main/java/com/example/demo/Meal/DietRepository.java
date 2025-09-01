package com.example.demo.Meal;

import com.example.demo.member.Member;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DietRepository extends JpaRepository<Diet, Long> {

    // 로그인 사용자별 최신순
    List<Diet> findAllByMemberOrderByDietIdDesc(Member member);

    List<Diet> findAllByOrderByDietIdDesc();
}
