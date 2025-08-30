package com.example.demo.Food.Service;

import com.example.demo.Food.model.dto.FoodResponseDto;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.Map;


@Service
public class FoodService {

    private final RestTemplate restTemplate = new RestTemplate();
    // FastAPI 서버의 정확한 URL과 엔드포인트를 지정합니다.
    private final String fastApiUrl = "http://localhost:8000/analyze-image/";

    public FoodResponseDto analyzeFood(MultipartFile file) throws IOException {
        // HTTP 요청 헤더 설정
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        // MultipartFile을 File로 변환하여 요청 본문에 추가
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        File tempFile = convertMultipartFileToFile(file);
        body.add("file", new FileSystemResource(tempFile));

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        // FastAPI 호출 및 응답 받기
        ResponseEntity<Map> response = restTemplate.postForEntity(fastApiUrl, requestEntity, Map.class);
        Map<String, Object> result = response.getBody();

        // 임시 파일 삭제
        if (tempFile.exists()) {
            tempFile.delete();
        }

        // FastAPI 응답에서 데이터 추출 (key 값은 FastAPI에서 반환하는 JSON key와 일치해야 합니다.)
        String foodName = (String) result.get("food_name");
        Double confidence = (Double) result.get("confidence");
        Integer calories = (Integer) result.get("calories");
        Integer carbohydrates = (Integer) result.get("carbohydrates");
        Integer protein = (Integer) result.get("protein");
        Integer fat = (Integer) result.get("fat");

        // DTO에 담아 클라이언트에 반환할 데이터 생성
        return FoodResponseDto.builder()
                .name(foodName)
                .confidenceScore((int) (confidence * 100))
                .servingSize("1 serving") // 더미 값 또는 실제 데이터
                .calories(calories)
                .carbohydrates(carbohydrates)
                .protein(protein)
                .fat(fat)
                .analysisDetails("FastAPI 모델이 예측한 결과입니다.")
                .build();
    }

    /**
     * MultipartFile을 임시 File로 변환하는 헬퍼 메서드.
     */
    private File convertMultipartFileToFile(MultipartFile file) throws IOException {
        File tempFile = File.createTempFile(file.getOriginalFilename(), "");
        file.transferTo(tempFile);
        return tempFile;
    }
}