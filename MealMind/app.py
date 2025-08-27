import os, json, datetime, re, ast
from typing import Optional, Dict, List, Union, Any
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---- 설정 ----
USE_OLLAMA   = os.getenv("USE_OLLAMA", "0")  # 기본 MOCK
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

app = FastAPI(title="MealMind Diet Recommender")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080","http://127.0.0.1:8080"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ---- 스키마 ----
class PrevMeal(BaseModel):
    carbs_g: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sodium_mg: Optional[float] = None

class RecommendBody(BaseModel):
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    previous_day: Optional[Dict[str, PrevMeal]] = None
    note: Optional[str] = None

# ---- 유틸 ----
@app.get("/ping")
def ping():
    return JSONResponse({"ok": True}, media_type="application/json; charset=utf-8")

def compute_goal_calories(gender, age, height_cm, weight_kg) -> int:
    gender = (gender or "female").lower()
    age = int(age or 25)
    h_cm = float(height_cm or 165.0)
    w_kg = float(weight_kg or 62.0)
    h_m = h_cm / 100.0
    bmi = w_kg / (h_m*h_m)
    target_w = 22.0*(h_m*h_m) if bmi >= 25 else (21.0*(h_m*h_m) if bmi < 18.5 else w_kg)
    s = 5 if gender.startswith("m") else -161
    bmr = 10*target_w + 6.25*h_cm - 5*age + s
    tdee = bmr * 1.4
    if bmi >= 25: goal = tdee * 0.85
    elif bmi < 18.5: goal = tdee * 1.10
    else: goal = tdee
    return int(round(goal/50.0)*50)

def _strip_code_fences(s: str) -> str:
    s = s.strip()
    m = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", s, re.IGNORECASE)
    return m.group(1) if m else s

def _loads_loose(s: str) -> Any:
    if not s: return None
    s = _strip_code_fences(s)
    l, r = s.find("{"), s.rfind("}")
    if l != -1 and r != -1 and r > l: s = s[l:r+1]
    try:
        return json.loads(s)
    except Exception:
        try:
            return ast.literal_eval(s)  # {"a":1} 같은 파이썬 dict 형태도 수용
        except Exception:
            return None

def _normalize_llm_content(content: Union[str, dict, list, bytes]) -> Optional[dict]:
    if isinstance(content, dict): return content
    if isinstance(content, list):
        for it in content:
            if isinstance(it, dict): return it
        return _loads_loose("\n".join(str(x) for x in content))
    if isinstance(content, (bytes, bytearray)):
        try: s = content.decode("utf-8", errors="ignore")
        except Exception: s = str(content)
        return _loads_loose(s)
    if isinstance(content, str): return _loads_loose(content)
    return None

def _chat_ollama(messages: List[dict]) -> Union[str, dict]:
    r = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3},
            "format": "json"  # JSON 강제
        },
        timeout=90
    )
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "")

def _coerce_int(x, default=0):
    try: return int(round(float(x)))
    except Exception: return default

def _ensure_schema(d: dict, goal: int, date: str) -> dict:
    d = dict(d or {})
    d.setdefault("date", date)
    d.setdefault("goal_calories", goal)
    d.setdefault("comment", "")
    for meal in ("breakfast","lunch","dinner"):
        d.setdefault(meal, {})
        m = d[meal] = dict(d[meal] or {})
        m.setdefault("menu","")
        m.setdefault("kcal",0)
        m["kcal"] = _coerce_int(m["kcal"], 0)
        m.setdefault("nutrients", {})
        n = m["nutrients"] = dict(m["nutrients"] or {})
        for k in ("carbs_g","protein_g","fat_g","fiber_g","sodium_mg"):
            n.setdefault(k, 0); n[k] = _coerce_int(n[k], 0)
    # 합계 보정
    d["total_kcal"] = _coerce_int(
        d.get("total_kcal", d["breakfast"]["kcal"] + d["lunch"]["kcal"] + d["dinner"]["kcal"]), 0
    )
    return d

# ---- 메인 엔드포인트 ----
@app.post("/recommend")
def recommend(body: RecommendBody,
              live: bool = Query(False, description="true면 모델 호출"),
              debug: bool = Query(False, description="true면 모델 원문 반환")):
    use_live = live or (USE_OLLAMA == "1")
    goal  = compute_goal_calories(body.gender, body.age, body.height_cm, body.weight_kg)
    today = datetime.date.today().isoformat()

    # MOCK
    if not use_live:
        parsed = {
            "date": today, "goal_calories": goal,
            "comment": "MOCK: 모델 비활성. 전날 아침 탄수 보정 반영.",
            "breakfast": {"menu":"현미밥 150g + 계란 2개","kcal": int(goal*0.3),
                          "nutrients":{"carbs_g":60,"protein_g":28,"fat_g":18,"fiber_g":6,"sodium_mg":900}},
            "lunch": {"menu":"닭가슴살 샐러드 + 고구마 150g","kcal": int(goal*0.4),
                      "nutrients":{"carbs_g":55,"protein_g":35,"fat_g":15,"fiber_g":8,"sodium_mg":850}},
            "dinner":{"menu":"잡곡밥 120g + 연어구이 120g","kcal": goal - int(goal*0.3) - int(goal*0.4),
                      "nutrients":{"carbs_g":45,"protein_g":32,"fat_g":16,"fiber_g":7,"sodium_mg":950}}
        }
        parsed["total_kcal"] = parsed["breakfast"]["kcal"] + parsed["lunch"]["kcal"] + parsed["dinner"]["kcal"]
        return JSONResponse(parsed, media_type="application/json; charset=utf-8")

    try:
        sys_prompt = (
            "너는 영양사다. 오직 JSON만 출력(문장/설명/마크다운 금지). "
            "키는 {date, goal_calories, comment, breakfast, lunch, dinner, total_kcal}. "
            "각 끼니는 {menu, kcal, nutrients{carbs_g, protein_g, fat_g, fiber_g, sodium_mg}}. "
            "총열량은 goal_calories ±5%, 끼니 배분 30/40/30. "
            "전날 일부 끼니만 주어지면 해당 끼니만 보정, 나머지는 평균 가정."
        )
        payload = {
            "date": today, "goal_calories": goal,
            "user": {"gender": body.gender or "unknown","age": body.age or "unknown",
                     "height_cm": body.height_cm or "unknown","weight_kg": body.weight_kg or "unknown",
                     "note": body.note or ""},
            "previous_day": (body.previous_day or {})
        }
        messages = [
            {"role":"system","content":sys_prompt},
            {"role":"user","content":json.dumps(payload, ensure_ascii=False)}
        ]
        content = _chat_ollama(messages)

        if debug:
            printable = content if isinstance(content, (dict, list)) else (str(content)[:4000])
            return JSONResponse({"raw": printable}, media_type="application/json; charset=utf-8")

        parsed = _normalize_llm_content(content)
        if not parsed:
            raise ValueError(f"LLM returned non-JSON: {str(content)[:300]}")

        parsed = _ensure_schema(parsed, goal, today)
        return JSONResponse(parsed, media_type="application/json; charset=utf-8")

    except Exception as e:
        print("[LLM][ERROR]", repr(e))
        fb = {
            "date": today, "goal_calories": goal,
            "comment": f"MODEL FALLBACK: {type(e).__name__}",
            "breakfast": {"menu":"현미밥 150g + 계란 2개","kcal": int(goal*0.3),
                          "nutrients":{"carbs_g":60,"protein_g":28,"fat_g":18,"fiber_g":6,"sodium_mg":900}},
            "lunch": {"menu":"닭가슴살 샐러드 + 고구마 150g","kcal": int(goal*0.4),
                      "nutrients":{"carbs_g":55,"protein_g":35,"fat_g":15,"fiber_g":8,"sodium_mg":850}},
            "dinner":{"menu":"잡곡밥 120g + 연어구이 120g","kcal": goal - int(goal*0.3) - int(goal*0.4),
                      "nutrients":{"carbs_g":45,"protein_g":32,"fat_g":16,"fiber_g":7,"sodium_mg":950}}
        }
        fb["total_kcal"] = fb["breakfast"]["kcal"] + fb["lunch"]["kcal"] + fb["dinner"]["kcal"]
        return JSONResponse(fb, media_type="application/json; charset=utf-8")
