from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import torch
from transformers import AutoTokenizer, BertForSequenceClassification
import httpx
import os

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
# 3️⃣ 모델 불러오기
# =========================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_DIR = "./kobert_emotion_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, use_fast=False, trust_remote_code=True)
model = BertForSequenceClassification.from_pretrained(MODEL_DIR, trust_remote_code=True)
model.to(device)
model.eval()

# 라벨 클래스 (학습 시 LabelEncoder.classes_와 동일하게)
label_classes = ["분노", "기쁨", "슬픔", "중립", "불안"]  # 예시

# =========================
# 4️⃣ Gemini API 설정
# =========================
API_KEY = os.getenv("API_KEY", "AIzaSyBB6Xxfls9a34gXycyP7uiex0OPXS8gXL4")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

async def call_gemini(emotion: str) -> str:
    prompt = (
        f"'{emotion}' 감정일 때 먹으면 좋은 음식 세 가지를 추천해줘. "
        f"각 음식은 번호를 붙이고, 음식 이름과 함께 왜 좋은지 간단한 설명을 덧붙여줘. "
        f"예시 형식:\n\n"
        f"1. 따뜻한 우유 한 잔\n설명...\n\n"
        f"2. 다크 초콜릿\n설명...\n\n"
        f"3. 고구마\n설명..."
    )
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{API_URL}?key={API_KEY}", json=payload, headers=headers)
            response.raise_for_status()

        response_json = response.json()
        return response_json["candidates"][0]["content"]["parts"][0]["text"].strip()

    except Exception as e:
        print(f"LLM API 호출 오류: {e}")
        raise HTTPException(status_code=500, detail="LLM API 호출 실패")

# =========================
# 5️⃣ 감정 예측 + 추천 API
# =========================
@app.post("/predict")
async def predict(req: TextRequest):
    # 1️⃣ 입력 토크나이징
    encoding = tokenizer(
        req.text,
        truncation=True,
        padding='max_length',
        max_length=64,
        return_tensors='pt'
    )
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    # 2️⃣ 모델 예측
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        pred_id = torch.argmax(outputs.logits, dim=1).item()

    pred_label = label_classes[pred_id]

    # 3️⃣ LLM 호출
    recommendation = await call_gemini(pred_label)

    # 4️⃣ 결과 반환
    return {
        "text": req.text,
        "predicted_emotion": pred_label,
        "recommendation": recommendation
    }

# =========================
# 6️⃣ 서버 실행
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
