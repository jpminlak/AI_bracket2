from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import joblib
import httpx # ✅ requests 대신 httpx 임포트
import os

# 모델 불러오기
try:
    model = joblib.load("emotion_model.pkl")
    vectorizer = joblib.load("tfidf_vectorizer.pkl")
except FileNotFoundError:
    raise FileNotFoundError("emotion_model.pkl 또는 tfidf_vectorizer.pkl 파일을 찾을 수 없습니다.")

app = FastAPI()

# ✅ CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 스키마
class TextRequest(BaseModel):
    text: str

# ✅ API 키는 환경 변수에서 로드하거나 여기에 직접 정의합니다.
API_KEY = os.getenv("API_KEY", "AIzaSyBB6Xxfls9a34gXycyP7uiex0OPXS8gXL4")
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

async def call_gemini(emotion: str) -> str:
    """
    비동기 방식으로 Gemini API를 호출하여 감정에 맞는 음식 추천(설명 포함)을 받는 함수
    """
    # 📌 프롬프트를 설명형으로 수정
    prompt = (
        f"'{emotion}' 감정일 때 먹으면 좋은 음식 세 가지를 추천해줘. "
        f"각 음식은 번호를 붙이고, 음식 이름과 함께 왜 좋은지 간단한 설명을 덧붙여줘. "
        f"예시 형식:\n\n"
        f"1. 따뜻한 우유 한 잔\n설명...\n\n"
        f"2. 다크 초콜릿\n설명...\n\n"
        f"3. 고구마\n설명..."
    )
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    try:
        # ✅ httpx.AsyncClient를 사용해 비동기 요청
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_URL}?key={API_KEY}",
                json=payload,
                headers=headers
            )
            response.raise_for_status() # HTTP 4xx/5xx 오류 발생 시 httpx.HTTPStatusError 발생

        response_json = response.json()

        # ✅ Gemini 응답에서 텍스트 부분만 추출
        full_text_response = response_json["candidates"][0]["content"]["parts"][0]["text"]

        return full_text_response.strip()

    except httpx.HTTPStatusError as e:
        # HTTP 오류(4xx, 5xx)가 발생했을 때 처리
        print(f"HTTP 오류 발생: {e.response.status_code}")
        print(f"응답 내용: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"LLM API 오류: {e.response.text}")
        
    except (KeyError, IndexError) as e:
        # 응답 JSON의 키가 없거나 구조가 예상과 다를 때 처리
        print(f"JSON 파싱 오류: {e}")
        print(f"응답 JSON: {response_json}")
        raise HTTPException(status_code=500, detail="LLM 응답 형식이 올바르지 않습니다.")

    except Exception as e:
        # 그 외 모든 예외를 처리
        print(f"예상치 못한 LLM API 호출 오류: {e}")
        raise HTTPException(status_code=500, detail="예상치 못한 서버 오류가 발생했습니다.")


@app.post("/predict")
async def predict(req: TextRequest): # ✅ 비동기 함수로 변경
    # 1️⃣ 감정 예측
    X_vec = vectorizer.transform([req.text])
    pred = model.predict(X_vec)[0]

    # 2️⃣ LLM 호출 (await 추가)
    recommendation = await call_gemini(pred)

    # 3️⃣ 결과 반환
    return {
        "text": req.text,
        "predicted_emotion": pred,
        "recommendation": recommendation
    }


# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
