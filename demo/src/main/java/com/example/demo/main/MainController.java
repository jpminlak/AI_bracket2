package com.example.demo.main;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class MainController {
    @GetMapping("/")
    public String mainPage() {
        System.out.println("메인 페이지");
        return "main";
    }

    @GetMapping("/terms")
    public String terms() {
        return "/footer/terms";
    }
}