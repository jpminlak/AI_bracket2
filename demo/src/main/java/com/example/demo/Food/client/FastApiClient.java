package com.example.demo.Food.client;//package Food.client;
//
//import Food.Service.MultipartInputStreamFileResource;
//import org.springframework.http.HttpEntity;
//import org.springframework.http.MediaType;
//import org.springframework.util.LinkedMultiValueMap;
//import org.springframework.util.MultiValueMap;
//import org.springframework.web.client.RestTemplate;
//import org.springframework.web.multipart.MultipartFile;
//
//import javax.print.attribute.standard.Media;
//import java.io.IOException;
//import java.net.http.HttpHeaders;
//import java.util.Map;
//
//public class FastApiClient {
//
//    private final RestTemplate restTemplate = new RestTemplate();
//    private final String fastApiUrl = "http://localhost:8000/food/upload";
//
//    public Map<String, Object> sendImage(MultipartFile file) throws IOException {
//        HttpHeaders headers = 으으new HttpHeaders();
//        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
//
//        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
//        body.add("file", new MultipartInputStreamFileResource(file.getInputStream(), file.getOriginalFilename()));
//
//        HttpEntity<MultiValueMap<String,Object>> requestEntity = new HttpEntity<>(body, headers);
//
//        return restTemplate.postForObject(fastApiUrl, requestEntity, Map.class);
//    }
//}
