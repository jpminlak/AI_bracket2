package com.example.demo.food.Service;

import com.example.demo.food.model.dto.FoodResponseDto;
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
public class FoodService {

    private final RestTemplate restTemplate = new RestTemplate();
    private final String fastApiUrl = "http://localhost:8000/upload"; // FastAPI URL

    public FoodResponseDto analyzeFood(MultipartFile file) throws IOException {
        File tempFile = convertMultipartFileToFile(file);
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);

            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            body.add("file", new FileSystemResource(tempFile));

            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
            ResponseEntity<Map> response = restTemplate.postForEntity(fastApiUrl, requestEntity, Map.class);

            Map<String, Object> result = response.getBody();
            if (result == null) throw new IOException("FastAPI에서 응답이 없습니다.");

            // FastAPI JSON key 기준
            String foodName = (String) result.get("food_name");
            Double confidence = result.get("confidence") instanceof Number ? ((Number) result.get("confidence")).doubleValue() : null;

            Map<String, Object> nutrition = result.get("nutrition_info") instanceof Map ?
                    (Map<String, Object>) result.get("nutrition_info") : Collections.emptyMap();

            Double calories = nutrition.get("calories") instanceof Number ? ((Number) nutrition.get("calories")).doubleValue() : null;
            Double protein = nutrition.get("protein") instanceof Number ? ((Number) nutrition.get("protein")).doubleValue() : null;
            Double fat = nutrition.get("fat") instanceof Number ? ((Number) nutrition.get("fat")).doubleValue() : null;
            Double carbohydrates = nutrition.get("carbohydrates") instanceof Number ? ((Number) nutrition.get("carbohydrates")).doubleValue() : null;

            return FoodResponseDto.builder()
                    .name(foodName)
                    .confidenceScore(confidence != null ? (int) (confidence * 100) : null)
                    .calories(calories)
                    .protein(protein)
                    .fat(fat)
                    .carbohydrates(carbohydrates)
                    .analysisDetails("FastAPI 모델 예측 결과")
                    .build();

        } finally {
            if (tempFile.exists()) tempFile.delete();
        }
    }

    private File convertMultipartFileToFile(MultipartFile file) throws IOException {
        String[] nameParts = file.getOriginalFilename().split("\\.");
        String prefix = nameParts[0];
        String suffix = nameParts.length > 1 ? "." + nameParts[1] : null;
        File tempFile = File.createTempFile(prefix, suffix);
        file.transferTo(tempFile);
        return tempFile;
    }
}
