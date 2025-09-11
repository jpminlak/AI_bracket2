package com.example.demo.inquiry;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface InquiryRepository extends JpaRepository<Inquiry, Long> {
    List<Inquiry> findAllByAnsweredFalse();

    @Query("SELECT i FROM Inquiry i JOIN FETCH i.member WHERE i.id = :id")
    Optional<Inquiry> findByIdWithMember(@Param("id") Long id);

    //@Query("SELECT i FROM Inquiry i JOIN FETCH i.member")
    //List<Inquiry> findAllWithMember();

    @Query("SELECT i FROM Inquiry i JOIN FETCH i.member")
    Page<Inquiry> findAllWithMember(Pageable pageable);

}