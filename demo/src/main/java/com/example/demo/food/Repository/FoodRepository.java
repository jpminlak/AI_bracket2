package com.example.demo.food.Repository;

import com.example.demo.food.model.Food;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface FoodRepository extends JpaRepository<Food, Long> {

    // 기존: 오늘 이후(regDate > todayStart) 끼니별 최근 5개
    List<Food> findTop5ByMember_NumAndMealTimeAndRegDateAfterOrderByRegDateDesc(
            Long memberNum, String mealTime, LocalDateTime from
    );

    // 🔹 추가: '어제 00:00 ~ 오늘 00:00' 등 임의의 일자 범위로 전날 전체 섭취 기록 조회
    List<Food> findByMember_NumAndRegDateBetween(
            Long memberNum, LocalDateTime start, LocalDateTime end
    );
}
