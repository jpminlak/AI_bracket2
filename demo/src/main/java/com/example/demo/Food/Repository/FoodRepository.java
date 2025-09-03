package com.example.demo.food.Repository;

import com.example.demo.food.model.Food;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface FoodRepository extends JpaRepository<Food, Long> {
    List<Food> findTop5ByMember_NumAndMealTimeAndRegDateAfterOrderByRegDateDesc(
            Long memberNum, String mealTime, LocalDateTime from);
}