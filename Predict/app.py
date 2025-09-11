from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import torch
from transformers import AutoTokenizer, BertForSequenceClassification
import torch.nn.functional as F
import httpx
import os
import re

# database.py에서 필요한 객체를 import
# 이 import 문이 실행될 때 database.py가 바로 실행되어 모든 변수를 초기화합니다.
from database import index, retriever, doc_texts, doc_labels


# =========================
# 1️⃣ FastAPI 초기화 + CORS
# =========================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 2️⃣ 요청 스키마
# =========================
class TextRequest(BaseModel):
    text: str


# =========================
# 3️⃣ 모델 로딩 (감정 분류 모델)
# =========================
# 서버 시작 시 모델 로딩
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_DIR = "./kobert_emotion_model"


# 토크나이저
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=True, local_files_only=True)
except Exception:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=False, trust_remote_code=True, local_files_only=True)

# 모델
model = BertForSequenceClassification.from_pretrained(MODEL_DIR, trust_remote_code=True, local_files_only=True)
model.to(device)
model.eval()


# 라벨 클래스 및 키워드
label_classes = ['공포', '놀람', '분노', '슬픔', '중립', '행복', '혐오']
emotion_keywords = {
    "분노": ["짜증", "열받", "빡치", "화나", "어이없", "화가"],
    "슬픔": ["슬퍼", "우울", "상심", "속상", "눈물"],
    "행복": ["행복", "좋아", "즐거", "기쁘", "신남"],
    "공포": ["무서", "겁나", "두려", "소름"],
    "놀람": ["놀라", "헉", "어머", "와우"],
    "혐오": ["역겹", "싫어", "구역질", "짜증"]
}
negation_words = ["안", "못", "없", "아니", "지않"]


# =========================
# 4️⃣ 서버 시작 이벤트
# =========================
# 이전에 있던 @app.on_event("startup")와 startup_event() 함수를 제거했습니다.
# database.py에서 변수를 직접 로드하므로 별도의 초기화 이벤트가 필요 없습니다.


# =========================
# 5️⃣ Gemini API 설정
# =========================

API_KEY = os.getenv("API_KEY", "AIzaSyBB6Xxfls9a34gXycyP7uiex0OPXS8gXL4")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

async def call_gemini(emotion: str) -> str:
    # database.py에서 불러온 retriever와 index를 사용
    if index is None or retriever is None:
        raise HTTPException(status_code=500, detail="Vector DB not initialized.")
        
    query_embedding = retriever.encode(emotion, convert_to_tensor=True).cpu().numpy().reshape(1, -1)
    distances, indices = index.search(query_embedding, k=1)
    
    retrieved_doc_index = indices[0][0]
    retrieved_emotion_label = doc_labels[retrieved_doc_index]
    context = doc_texts[retrieved_doc_index]
    
    print(f"예측된 감정: {emotion}, 검색된 문서 라벨: {retrieved_emotion_label}")
    print(f"검색된 문서 내용:\n{context}")
    
    prompt = (
    f"다음은 '{retrieved_emotion_label}' 감정에 대한 배경 설명이야:\n{context}\n\n"
    f"이 감정에 맞는 음식을 세 가지 추천해줘. "
    f"각 음식은 번호를 붙이고, 음식 이름과 간단한 이유를 덧붙여줘."
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{API_URL}?key={API_KEY}", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"LLM API 호출 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM API 호출 실패")


# =========================
# 6️⃣ 감정 예측 + 추천 API
# =========================

def adjust_emotion_by_keywords(text: str, probs: torch.Tensor) -> torch.Tensor:
    text_proc = re.sub(r"\s+", "", text)
    for idx, label in enumerate(label_classes):
        for kw in emotion_keywords.get(label, []):
            if kw in text_proc:
                neg = any(text_proc.find(nw + kw) != -1 for nw in negation_words)
                if neg:
                    probs[idx] *= 0.3
                else:
                    probs[idx] += 0.3
                    
    probs = probs / probs.sum()
    return probs

@app.post("/predict")
async def predict(req: TextRequest):
    try:
        text = req.text.strip()
        
        encoding = tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=256,
            return_tensors="pt"
        )
        
        input_ids = encoding['input_ids'].to(device)
        attention_mask = encoding['attention_mask'].to(device)

        with torch.no_grad():
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = F.softmax(logits, dim=1)[0]

        probs = adjust_emotion_by_keywords(text, probs)

        pred_id = int(probs.argmax())
        pred_label = label_classes[pred_id]

        recommendation = await call_gemini(pred_label)

        return {
            "predicted_emotion": pred_label,
            "recommendation": recommendation
        }

    except Exception as e:
        print(f"예측 오류: {e}")
        raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")


# =========================
# 7️⃣ 서버 실행
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)