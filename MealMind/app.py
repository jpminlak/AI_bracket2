# app.py
# --------------------------------------------
# MealMind: FastAPI + Ollama(JSON 안정화 버전)
# --------------------------------------------
from __future__ import annotations # 파이썬의 미래 문법(타입힌트 전방참조)을 켜서 타입 표기가 더 유연해지게 함.
import os, re, json, math, requests # 표준 라이브러리(환경변수, 정규식, JSON, 수학)와 HTTP 요청용 requests 임포트.
from typing import Any, Dict, Optional # 타입힌트용 임포트.

from fastapi import FastAPI, Body, Query # FastAPI와 관련된 클래스 및 함수 임포트.
from pydantic import BaseModel, Field # 데이터 검증 및 설정 관리를 위한 Pydantic 임포트.
import uvicorn # ASGI 서버인 Uvicorn 임포트.

# ===== 환경설정 =====
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
APP_PORT = int(os.getenv("PORT", "8001"))

# ===== FastAPI =====
app = FastAPI(title="MealMind API", version="1.1.0")

# ===== Pydantic 모델 =====
class RecommendRequest(BaseModel):
    gender: str = Field(..., description="male/female (자유 문자열 허용)")
    age: int = Field(..., ge=1, le=120)
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    activity_level: Optional[str] = Field(
        default="light",
        description="sedentary/light/moderate/active/very_active (옵션)"
    )

class Nutrients(BaseModel):
    carbs_g: int
    protein_g: int
    fat_g: int
    fiber_g: int
    sodium_mg: int

class Meal(BaseModel):
    menu: str
    kcal: int
    nutrients: Nutrients

class RecommendResponse(BaseModel):
    breakfast: Meal
    lunch: Meal
    dinner: Meal
    total_kcal: int
    goal_calories: int
    comment: str

# ===== 유틸: JSON 느슨 파서 =====
def _parse_json_loose(s: str) -> Dict[str, Any]:
    """
    - 코드펜스/앞뒤 잡소리 제거
    - 가장 바깥 {...}만 추출
    - 최종 json.loads()
    """
    t = (s or "").strip()
    # 코드펜스 제거
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE | re.DOTALL).strip()
    # 가장 바깥 {} 추출
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1 and i < j:
        t = t[i:j + 1]
    return json.loads(t)

# ===== 유틸: 목표 칼로리(대략) =====
def _bmr_mifflin(gender: str, age: int, height_cm: float, weight_kg: float) -> float:
    if gender.lower().startswith("m"):  # male
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161  # female

def _activity_factor(level: str) -> float:
    level = (level or "").lower()
    return {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }.get(level, 1.375)

def calc_goal_calories(req: RecommendRequest) -> int:
    bmr = _bmr_mifflin(req.gender, req.age, req.height_cm, req.weight_kg)
    tdee = bmr * _activity_factor(req.activity_level)
    # 딱 떨어지게 반올림
    return int(round(tdee / 10.0) * 10)

# ===== 프롬프트 =====
def build_prompt_open(req: RecommendRequest, goal: int) -> str:
    return f"""
역할: 당신은 한국인 일반식을 기준으로 1일 3끼 식단을 설계하는 영양 코치입니다.
조건:
- 사용자의 성별/나이/키/몸무게/활동수준에 맞춰 3끼 식단을 추천하세요.
- 각 끼니는 '메뉴 문자열', '칼로리', '영양소(탄수화물g/단백질g/지방g/식이섬유g/나트륨mg)'만 제공합니다.
- 출력은 오직 JSON 오브젝트 하나만 반환하세요. 코드펜스나 주석/설명 금지.
입력:
- gender: {req.gender}
- age: {req.age}
- height_cm: {req.height_cm}
- weight_kg: {req.weight_kg}
- activity_level: {req.activity_level}
- goal_calories: {goal}

반환 스키마 예시(JSON):
{{
  "breakfast": {{
    "menu": "현미밥 120g + 계란 2개 + 야채샐러드 100g",
    "kcal": 460,
    "nutrients": {{"carbs_g": 64, "protein_g": 20, "fat_g": 13, "fiber_g": 6, "sodium_mg": 230}}
  }},
  "lunch": {{
    "menu": "잡곡밥 120g + 닭가슴살 120g + 구운 야채 120g",
    "kcal": 520,
    "nutrients": {{"carbs_g": 62, "protein_g": 44, "fat_g": 7, "fiber_g": 6, "sodium_mg": 170}}
  }},
  "dinner": {{
    "menu": "연어구이 120g + 고구마 150g + 된장찌개 1컵",
    "kcal": 465,
    "nutrients": {{"carbs_g": 38, "protein_g": 34, "fat_g": 17, "fiber_g": 5, "sodium_mg": 920}}
  }},
  "total_kcal": 1445,
  "goal_calories": {goal},
  "comment": "하루 목표 대비 균형적으로 구성했습니다."
}}
주의: 위는 포맷 예시일 뿐이며, 실제 추천은 사용자 조건에 맞춘 값으로 생성하세요.
""".strip()

# ===== Ollama 호출 =====
def call_ollama_json(prompt: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    - Ollama /api/generate 호출
    - 가능하면 format=json 유도
    - 실패/비JSON 응답 시 느슨 파서로 재시도
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        # 일부 모델은 format="json"을 지원: 유효하면 깔끔한 JSON, 아니면 무시되고 일반 텍스트
        "format": "json",
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 50,
            "repeat_penalty": 1.15,
            "num_predict": 320,
            "stop": ["```"]
        }
    }
    if options:
        payload["options"].update(options)

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    resp = data.get("response", "")

    # 1) 이미 dict인 경우
    if isinstance(resp, dict):
        return resp
    # 2) 문자열이면 느슨 파싱
    try:
        return _parse_json_loose(resp)
    except Exception as e:
        # 최후의 시도: 그냥 json.loads (혹시 완전한 JSON 문자열일 수 있으니)
        return json.loads(resp)

# ===== 정규화 =====
def _coerce_int(x, default=0) -> int:
    try:
        return int(round(float(x)))
    except Exception:
        return default

def normalize_response(obj: Dict[str, Any], goal: int) -> RecommendResponse:
    def _meal(key: str) -> Meal:
        m = obj.get(key, {}) or {}
        menu = str(m.get("menu", "메뉴 정보 없음")).strip()
        kcal = _coerce_int(m.get("kcal"), 0)

        n = m.get("nutrients", {}) or {}
        nutrients = Nutrients(
            carbs_g=_coerce_int(n.get("carbs_g"), 0),
            protein_g=_coerce_int(n.get("protein_g"), 0),
            fat_g=_coerce_int(n.get("fat_g"), 0),
            fiber_g=_coerce_int(n.get("fiber_g"), 0),
            sodium_mg=_coerce_int(n.get("sodium_mg"), 0),
        )
        return Meal(menu=menu, kcal=kcal, nutrients=nutrients)

    breakfast = _meal("breakfast")
    lunch = _meal("lunch")
    dinner = _meal("dinner")

    total_kcal = _coerce_int(obj.get("total_kcal"), breakfast.kcal + lunch.kcal + dinner.kcal)
    goal_calories = _coerce_int(obj.get("goal_calories"), goal)
    comment = str(obj.get("comment") or "모델 응답").strip()

    return RecommendResponse(
        breakfast=breakfast, lunch=lunch, dinner=dinner,
        total_kcal=total_kcal, goal_calories=goal_calories, comment=comment
    )

# ===== 폴백 =====
def fallback_response(goal: int) -> RecommendResponse:
    # 스크린샷과 동일한 폴백 메뉴
    return RecommendResponse(
        breakfast=Meal(
            menu="현미밥 120g + 계란 2개 + 야채샐러드 100g",
            kcal=460,
            nutrients=Nutrients(carbs_g=64, protein_g=20, fat_g=13, fiber_g=6, sodium_mg=230),
        ),
        lunch=Meal(
            menu="잡곡밥 120g + 닭가슴살 120g + 구운 야채 120g",
            kcal=520,
            nutrients=Nutrients(carbs_g=62, protein_g=44, fat_g=7, fiber_g=6, sodium_mg=170),
        ),
        dinner=Meal(
            menu="연어구이 120g + 고구마 150g + 된장찌개 1컵",
            kcal=465,
            nutrients=Nutrients(carbs_g=38, protein_g=34, fat_g=17, fiber_g=5, sodium_mg=920),
        ),
        total_kcal=1445,
        goal_calories=goal,
        comment="MODEL FALLBACK: JSONDecodeError",
    )

# ===== 서비스 로직 =====
def open_mode_recommend(req: RecommendRequest) -> RecommendResponse:
    goal = calc_goal_calories(req)
    prompt = build_prompt_open(req, goal)

    # 모델 호출 + 정규화
    raw = call_ollama_json(prompt)
    return normalize_response(raw, goal)

# ===== 엔드포인트 =====
@app.get("/ping")
def ping():
    return {"ok": True}

@app.post("/recommend", response_model=RecommendResponse)
def recommend(
    payload: RecommendRequest = Body(...),
    live: bool = Query(False, description="스프링에서 live=true로 호출")
):
    try:
        res = open_mode_recommend(payload)
        if live:
            # 라이브 호출 티만 남김
            if not res.comment:
                res.comment = "LIVE"
            else:
                res.comment = f"LIVE: {res.comment}"
        return res
    except Exception as e:
        # 모든 예외 → 폴백
        goal = calc_goal_calories(payload)
        fb = fallback_response(goal)
        if live:
            fb.comment = f"MODEL FALLBACK: {type(e).__name__}"
        return fb

# ===== 스타트업 워밍업 (선택) =====
@app.on_event("startup")
def _warm_up():
    try:
        # 서버 자신에게 워밍업 리퀘스트 (비동기 아님: 실패해도 그냥 지나감)
        url = f"http://127.0.0.1:{APP_PORT}/recommend?live=true"
        sample = {
            "gender": "female",
            "age": 21,
            "height_cm": 162,
            "weight_kg": 52,
            "activity_level": "light"
        }
        requests.post(url, json=sample, timeout=5)
    except Exception:
        pass

# ===== 메인 =====
if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=APP_PORT, reload=False)
