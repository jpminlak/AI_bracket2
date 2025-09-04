package com.example.demo.Food.Service;

import com.example.demo.Food.Repository.FoodRepository;
import com.example.demo.Food.model.Food;
import com.example.demo.Food.model.dto.FoodResponseDto;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.Collections;
import java.util.Map;


@Service
@RequiredArgsConstructor
@Transactional  // 트랜잭션 보장
public class FoodService {

    private final FoodRepository foodRepository;
    private final RestTemplate restTemplate = new RestTemplate();
    private final String fastApiUrl = "http://localhost:8000/upload";

    public FoodResponseDto analyzeFood(MultipartFile file) throws IOException {
        File tempFile = convertMultipartFileToFile(file);
        try {
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new FileSystemResource(tempFile));
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.postForEntity(fastApiUrl, request, Map.class);

            Map<String, Object> result = response.getBody();
            if (result == null) throw new IOException("FastAPI 응답 없음");

            String foodName = (String) result.get("food_name"); // FastAPI JSON 키 확인
            Map<String, Object> nutrition = (Map<String, Object>) result.getOrDefault("nutrition_info", Collections.emptyMap());

            Food foodEntity = Food.builder()
                    .foodName(foodName)
                    .calories(toDouble(nutrition.get("calories")))
                    .protein(toDouble(nutrition.get("protein")))
                    .fat(toDouble(nutrition.get("fat")))
                    .carbohydrates(toDouble(nutrition.get("carbohydrates")))
                    .build();

            System.out.println("저장할 음식: " + foodEntity); // DB 저장 전 로그
            foodRepository.save(foodEntity); // DB 저장

            return FoodResponseDto.builder()
                    .name(foodName)
                    .confidenceScore(toConfidence(result.get("confidence")))
                    .calories(foodEntity.getCalories())
                    .protein(foodEntity.getProtein())
                    .fat(foodEntity.getFat())
                    .carbohydrates(foodEntity.getCarbohydrates())
                    .analysisDetails("FastAPI 모델 예측 결과")
                    .build();

        } finally {
            if (tempFile.exists()) tempFile.delete();
        }
    }

    private File convertMultipartFileToFile(MultipartFile file) throws IOException {
        File tempFile = File.createTempFile("upload-", file.getOriginalFilename());
        file.transferTo(tempFile);
        return tempFile;
    }

    private Double toDouble(Object obj) {
        if (obj instanceof Number) return ((Number) obj).doubleValue();
        return null;
    }

    private Integer toConfidence(Object obj) {
        if (obj instanceof Number) return (int)(((Number) obj).doubleValue() * 100);
        return null;
    }
}
