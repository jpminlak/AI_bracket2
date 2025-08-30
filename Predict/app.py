from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import torch
from transformers import AutoTokenizer, BertForSequenceClassification
import torch.nn.functional as F
import httpx
import os
import re

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
# 3️⃣ 모델 로딩
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_DIR = "./kobert_emotion_model"

# 토크나이저
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=True)
except Exception:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=False, trust_remote_code=True)

# 모델
model = BertForSequenceClassification.from_pretrained(MODEL_DIR, trust_remote_code=True)
model.to(device)
model.eval()

# 라벨 클래스
label_classes = ['공포', '놀람', '분노', '슬픔', '중립', '행복', '혐오']

# 감정 키워드
emotion_keywords = {
    "분노": ["짜증", "열받", "빡치", "화나", "어이없", "화가"],
    "슬픔": ["슬퍼", "우울", "상심", "속상", "눈물"],
    "행복": ["행복", "좋아", "즐거", "기쁘", "신남"],
    "공포": ["무서", "겁나", "두려", "소름"],
    "놀람": ["놀라", "헉", "어머", "와우"],
    "혐오": ["역겹", "싫어", "구역질", "짜증"]
}

# 부정어/반전
negation_words = ["안", "못", "없", "아니", "지않"]

# =========================
# 4️⃣ Gemini API 설정
# =========================
API_KEY = os.getenv("API_KEY", "AIzaSyBB6Xxfls9a34gXycyP7uiex0OPXS8gXL4")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

async def call_gemini(emotion: str) -> str:
    prompt = (
        f"'{emotion}' 감정일 때 먹으면 좋은 음식 세 가지를 추천해줘. "
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
# 5️⃣ 감정 예측 + 추천 API
# =========================
def adjust_emotion_by_keywords(text: str, probs: torch.Tensor) -> torch.Tensor:
    text_proc = re.sub(r"\s+", "", text)  # 공백 제거
    for idx, label in enumerate(label_classes):
        for kw in emotion_keywords.get(label, []):
            if kw in text_proc:
                # 부정어 확인
                neg = any(text_proc.find(nw + kw) != -1 for nw in negation_words)
                if neg:
                    # 부정이면 해당 감정 확률 감소
                    probs[idx] *= 0.3
                else:
                    # 일반 키워드면 확률 증가
                    probs[idx] += 0.3
    # 정규화
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

        # 키워드 + 부정어 보정
        probs = adjust_emotion_by_keywords(text, probs)

        pred_id = int(probs.argmax())
        pred_label = label_classes[pred_id]

        # LLM 추천
        recommendation = await call_gemini(pred_label)

        return {
            "text": text,
            "predicted_emotion": pred_label,
            "emotion_probs": {label_classes[i]: float(f"{probs[i]:.3f}") for i in range(len(label_classes))},
            "recommendation": recommendation
        }

    except Exception as e:
        print(f"예측 오류: {e}")
        raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")

# =========================
# 6️⃣ 서버 실행
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
