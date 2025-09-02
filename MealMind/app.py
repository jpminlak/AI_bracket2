# app.py
# ------------------------------------------------------------
# FastAPI: Diet recommendation service (gender/height/weight only)
# - GET  /ping
# - POST /recommend?live=true|false
# Response (backward-compatible for Java):
# {
#   "breakfast": {"menu":"...", "kcal":0, "nutrients":{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}},
#   "lunch":     {"menu":"...", "kcal":0, "nutrients":{...}},
#   "dinner":    {"menu":"...", "kcal":0, "nutrients":{...}},
#   "total_kcal": 0,
#   "goal_kcal":  0,
#   "total_nutrients": {"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0},
#   "reason": "한 줄 설명"   # NEW
# }
# ------------------------------------------------------------
import os
import json
import re
from typing import Optional, Dict, Any, List

import uvicorn
import httpx
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Diet Recommender", version="1.4.0")

# ---------- Env (LLM) ----------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")
TIMEOUT_SEC = float(os.getenv("HTTP_TIMEOUT", "30"))

# =========================
# 1) Request
# =========================
class _PydanticV2ExtraIgnore(BaseModel):
    class Config:
        extra = "ignore"

class RecommendRequest(_PydanticV2ExtraIgnore):
    gender: str = Field(..., description="male/female or '여/남'")
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)

# =========================
# 2) Calorie & Nutrients
# =========================
def _normalize_gender(g: str) -> str:
    if not g:
        return "female"
    s = g.strip().lower()
    if s in ("남", "m", "male", "man", "boy"):
        return "male"
    if s in ("여", "f", "female", "woman", "girl"):
        return "female"
    return "female"

def _bmr_mifflin(gender: str, height_cm: float, weight_kg: float, age: int = 21) -> float:
    g = _normalize_gender(gender)
    if g == "male":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

def _activity_factor() -> float:
    return 1.375  # light

def calc_goal_calories(req: RecommendRequest) -> int:
    bmr = _bmr_mifflin(req.gender, req.height_cm, req.weight_kg, age=21)
    tdee = bmr * _activity_factor()
    return int(round(tdee / 10.0) * 10)

def _split_calories(total: int) -> Dict[str, int]:
    b = int(round(total * 0.30))
    l = int(round(total * 0.40))
    d = total - b - l
    return {"breakfast": b, "lunch": l, "dinner": d}

def _compute_fiber_g(kcal: int) -> int:
    return max(2, int(round(kcal / 1000.0 * 14)))

def _compute_nutrients(kcal: int, protein_ratio=0.25, carbs_ratio=0.50, fat_ratio=0.25) -> Dict[str, int]:
    protein_g = int(round(kcal * protein_ratio / 4.0))
    carbs_g   = int(round(kcal * carbs_ratio   / 4.0))
    fat_g     = int(round(kcal * fat_ratio     / 9.0))
    fiber_g   = _compute_fiber_g(kcal)
    return {"protein_g": protein_g, "carbs_g": carbs_g, "fat_g": fat_g, "fiber_g": fiber_g}

def _sum_nutrients(a: Dict[str, int], b: Dict[str, int]) -> Dict[str, int]:
    return {
        "protein_g": a.get("protein_g", 0) + b.get("protein_g", 0),
        "carbs_g":   a.get("carbs_g",   0) + b.get("carbs_g",   0),
        "fat_g":     a.get("fat_g",     0) + b.get("fat_g",     0),
        "fiber_g":   a.get("fiber_g",   0) + b.get("fiber_g",   0),
    }

# =========================
# 3) Menu normalization (1~4 items, Korean-friendly, coherent set)
# =========================
_DEFAULT_MEALS = {
    "breakfast": ["현미밥", "달걀국", "두부조림", "김치"],
    "lunch":     ["현미밥", "닭가슴살 불고기", "시금치나물", "김치"],
    "dinner":    ["잡곡밥", "연어구이", "구운채소", "미역국"],
}
_SPLIT_PATTERN = re.compile(r"[,\u00B7\u2022|/·・]+")

def _normalize_menu_value(val: Any, meal_key: str, max_items: int = 4) -> str:
    items: List[str]
    if isinstance(val, list):
        items = [str(x).strip() for x in val if str(x).strip()]
    else:
        s = str(val or "").strip()
        items = [t.strip() for t in _SPLIT_PATTERN.split(s) if t.strip()] if s else []
    if not items:
        items = _DEFAULT_MEALS.get(meal_key, [])[:max_items]
    items = items[:max_items]
    if not items:
        items = _DEFAULT_MEALS.get(meal_key, ["현미밥"])[:1]
    return ", ".join(items)

# =========================
# 4) LLM
# =========================
def build_prompt_open(req: RecommendRequest, goal: int) -> str:
    gender = _normalize_gender(req.gender)
    return f"""
You are a Korean diet planner. Generate a Korean-friendly daily meal plan as JSON.

Rules:
- Inputs: gender={gender}, height_cm={req.height_cm}, weight_kg={req.weight_kg}
- Total daily calories target: {goal} kcal
- Split: breakfast 30%, lunch 40%, dinner 30%
- Each meal is a coherent Korean set (don't mix toast with rice/국).
- 다양한 메뉴 추천 (항상 한식일 필요 없음) (예: 샐러드, 파스타, 스테이크, 볶음밥, 덮밥 등)
- Each "menu" has 1~4 items, comma-separated.
- Output STRICT JSON (no markdown):
{{
  "breakfast": {{"menu":"현미밥, 달걀국, 두부조림, 김치","kcal":500,"nutrients":{{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}}}},
  "lunch":     {{"menu":"현미밥, 닭가슴살 불고기, 시금치나물, 김치","kcal":700,"nutrients":{{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}}}},
  "dinner":    {{"menu":"잡곡밥, 연어구이, 구운채소, 미역국","kcal":600,"nutrients":{{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}}}},
  "total_kcal": 1800
}}
""".strip()

async def llm_complete_open(prompt: str) -> Optional[Dict[str, Any]]:
    url = f"{OLLAMA_HOST}/api/generate"
    body = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response", "") or data.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                m = re.search(r"\{.*\}", text, re.DOTALL)
                if m:
                    return json.loads(m.group(0))
    except Exception:
        pass
    return None

# =========================
# 5) Reason builder
# =========================
def _build_reason(goal_kcal: int, total_nutrients: Dict[str, int]) -> str:
    # 한 줄: 목표칼로리 적합 + 비율 + 한식 조합 + 섬유 보너스
    fiber = total_nutrients.get("fiber_g", 0)
    return (
        f"키·몸무게·성별로 계산한 목표 {goal_kcal} kcal에 맞춰 "
        f"탄수 50%·단백질 25%·지방 25% 비율로 구성했고, "
        f"밥·국·단백질·채소가 어우러지는 한식 조합으로 맛과 포만감을 균형 있게 설계했어요"
        + (f" (식이섬유≈{fiber} g)." if fiber else ".")
    )

# =========================
# 6) Fallback & Post-processing
# =========================
def _fallback_menu(goal_kcal: int) -> Dict[str, Any]:
    cal = _split_calories(goal_kcal)
    b_k, l_k, d_k = cal["breakfast"], cal["lunch"], cal["dinner"]
    b = {"menu": ", ".join(_DEFAULT_MEALS["breakfast"][:4]), "kcal": b_k, "nutrients": _compute_nutrients(b_k)}
    l = {"menu": ", ".join(_DEFAULT_MEALS["lunch"][:4]),     "kcal": l_k, "nutrients": _compute_nutrients(l_k)}
    d = {"menu": ", ".join(_DEFAULT_MEALS["dinner"][:4]),    "kcal": d_k, "nutrients": _compute_nutrients(d_k)}
    total_nut = _sum_nutrients(_sum_nutrients(b["nutrients"], l["nutrients"]), d["nutrients"])
    reason = _build_reason(goal_kcal, total_nut)
    return {
        "breakfast": b, "lunch": l, "dinner": d,
        "total_kcal": goal_kcal, "goal_kcal": goal_kcal,
        "total_nutrients": total_nut,
        "reason": reason,
    }

def _rescale_meals_to_goal(b: Dict[str, Any], l: Dict[str, Any], d: Dict[str, Any], goal_kcal: int):
    cur = int(b["kcal"]) + int(l["kcal"]) + int(d["kcal"])
    if cur <= 0:
        split = _split_calories(goal_kcal)
        b["kcal"], l["kcal"], d["kcal"] = split["breakfast"], split["lunch"], split["dinner"]
    else:
        if abs(cur - goal_kcal) > 200:
            factor = goal_kcal / float(cur)
            bk = int(round(b["kcal"] * factor))
            lk = int(round(l["kcal"] * factor))
            dk = goal_kcal - bk - lk
            b["kcal"], l["kcal"], d["kcal"] = bk, lk, dk
    # kcal 기반 영양소 재계산
    b["nutrients"] = _compute_nutrients(int(b["kcal"]))
    l["nutrients"] = _compute_nutrients(int(l["kcal"]))
    d["nutrients"] = _compute_nutrients(int(d["kcal"]))

def _ensure_shape_and_fit(js: Dict[str, Any], goal_kcal: int) -> Dict[str, Any]:
    def norm_menu(val: Any, key: str) -> str:
        return _normalize_menu_value(val, key)

    def norm_meal(key: str) -> Dict[str, Any]:
        m = js.get(key, {}) or {}
        kcal = int(m.get("kcal", 0))
        menu = norm_menu(m.get("menu", ""), key)
        nutrients = m.get("nutrients")
        if not isinstance(nutrients, dict) or kcal <= 0:
            nutrients = _compute_nutrients(max(kcal, 1))
        else:
            comp = _compute_nutrients(kcal)
            nutrients = {k: int(round(nutrients.get(k, comp[k]))) for k in comp.keys()}
        return {"menu": menu, "kcal": int(kcal), "nutrients": nutrients}

    b, l, d = norm_meal("breakfast"), norm_meal("lunch"), norm_meal("dinner")
    _rescale_meals_to_goal(b, l, d, goal_kcal)

    tk = int(b["kcal"] + l["kcal"] + d["kcal"])
    tn = _sum_nutrients(_sum_nutrients(b["nutrients"], l["nutrients"]), d["nutrients"])
    reason = _build_reason(goal_kcal, tn)

    return {
        "breakfast": b, "lunch": l, "dinner": d,
        "total_kcal": tk, "goal_kcal": goal_kcal,
        "total_nutrients": tn,
        "reason": reason,
    }

# =========================
# 7) Endpoints
# =========================
@app.get("/ping")
def ping():
    return {"ok": True}

@app.post("/recommend")
async def recommend(req: RecommendRequest, live: bool = Query(False, description="Use LLM if true")):
    goal = calc_goal_calories(req)
    if live:
        js = await llm_complete_open(build_prompt_open(req, goal))
        if isinstance(js, dict) and {"breakfast", "lunch", "dinner"}.issubset(js.keys()):
            try:
                return _ensure_shape_and_fit(js, goal_kcal=goal)
            except Exception:
                pass
    return _fallback_menu(goal)

# =========================
# 8) Dev entry
# =========================
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8001")), reload=True)
