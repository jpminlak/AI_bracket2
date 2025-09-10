package com.example.demo.Controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;

@Controller
public class EmotionController {

    @GetMapping("/emotion")
    public String emotion() {
        return "Emotion";
    }
}
