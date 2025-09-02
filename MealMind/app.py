# app.py
# ------------------------------------------------------------
# FastAPI: Diet recommendation service (gender/height/weight only)
# v1.6.0 — 끼니 조합(Coherence) 검증 및 자동 교정
# ------------------------------------------------------------
import os
import json
import re
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

import uvicorn
import httpx
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI(title="Diet Recommender", version="1.6.0")

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
# 3) Menu normalization (1~4 items, coherent set)
# =========================
_SPLIT_PATTERN = re.compile(r"[,\u00B7\u2022|/·・]+")  # 콤마/중점/슬래시 등

def _normalize_menu_value(val: Any, meal_key: str, max_items: int = 4) -> str:
    if isinstance(val, list):
        items = [str(x).strip() for x in val if str(x).strip()]
    else:
        s = str(val or "").strip()
        items = [t.strip() for t in _SPLIT_PATTERN.split(s) if t.strip()] if s else []
    items = items[:max_items] if items else []
    if not items:
        items = ["현미밥", "달걀국", "두부조림", "김치"][:max_items] if meal_key=="breakfast" else \
                ["현미밥", "닭가슴살 불고기", "시금치나물", "김치"][:max_items] if meal_key=="lunch" else \
                ["잡곡밥", "연어구이", "구운채소", "미역국"][:max_items]
    return ", ".join(items)

# ------- 스타일 키워드 & 코히어런스 체크 -------
STYLE_KEYWORDS: Dict[str, List[str]] = {
    "kr_rice":  ["밥", "현미밥", "잡곡밥", "쌀밥", "국", "탕", "찌개", "나물", "김치", "조림", "볶음", "구이", "무침"],
    "noodle":   ["국수", "우동", "라면", "라멘", "파스타", "칼국수", "냉면", "소바", "쌀국수", "짜장면", "짬뽕"],
    "bread":    ["토스트", "샌드위치", "버거", "프라이", "스테이크", "수프", "요거트", "오트밀", "리조또", "피자"],
    "salad":    ["샐러드", "샐러", "그릭요거트", "볼"],
    "japanese": ["초밥", "스시", "사시미", "돈까스", "돈가스", "돈카츠", "가츠", "규동", "텐동", "미소"],
}

def _style_of_item(item: str) -> str:
    s = item.strip().lower()
    for style, kws in STYLE_KEYWORDS.items():
        for kw in kws:
            if kw in s:
                return style
    return "unknown"

def _coherence_score(items: List[str]) -> float:
    tags = [t for t in (_style_of_item(x) for x in items) if t != "unknown"]
    if not tags:
        return 1.0
    from collections import Counter
    cnt = Counter(tags)
    return max(cnt.values()) / sum(cnt.values())

def _cohere_or_replace(meal_key: str, menu: str, rnd: random.Random) -> str:
    items = [t.strip() for t in _SPLIT_PATTERN.split(menu) if t.strip()]
    score = _coherence_score(items)
    if score >= 0.67:
        return ", ".join(items[:4])  # 적절
    # 지배 스타일 선택
    tags = [t for t in (_style_of_item(x) for x in items) if t != "unknown"]
    dominant = None
    if tags:
        from collections import Counter
        dominant = Counter(tags).most_common(1)[0][0]
    # fallback 후보 중 같은 스타일 우선 선택
    candidates = FALLBACK_BANK[meal_key][:]
    rnd.shuffle(candidates)
    def menu_style(m: str) -> str:
        its = [t.strip() for t in _SPLIT_PATTERN.split(m) if t.strip()]
        tags = [t for t in (_style_of_item(x) for x in its) if t != "unknown"]
        if not tags: return "unknown"
        from collections import Counter
        return Counter(tags).most_common(1)[0][0]
    if dominant:
        for c in candidates:
            if menu_style(c) == dominant:
                return c
    # 못 찾으면 아무거나(이미 후보는 모두 내부적으로 일관성 있음)
    return rnd.choice(candidates)

# =========================
# 4) LLM
# =========================
def build_prompt_open(req: RecommendRequest, goal: int) -> str:
    gender = _normalize_gender(req.gender)
    return f"""
You are a skilled diet planner for Korean users. Return STRICT JSON only.

Inputs:
- gender={gender}, height_cm={req.height_cm}, weight_kg={req.weight_kg}
Rules:
- Target total = {goal} kcal (±200 kcal OK). Split: breakfast 30%, lunch 40%, dinner 30%.
- Each meal MUST be ONE style among:
  (a) Korean rice set(밥+국+반찬), (b) Noodle set, (c) Bread/Western set,
  (d) Salad bowl, (e) Japanese set. Do NOT mix across styles within the SAME meal.
- Encourage VARIETY across meals (Korean/Western/Japanese/Salad/Pasta/덮밥 등).
- Do NOT repeat the same main dish across breakfast/lunch/dinner.
- The example below shows JSON SHAPE ONLY. DO NOT COPY ITS MENU.
- Each "menu" has 1~4 items, comma-separated. Use names familiar to Korean users.

Return JSON:
{{
  "breakfast": {{"menu":"현미밥, 달걀국, 두부조림, 김치","kcal":500,"nutrients":{{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}}}},
  "lunch":     {{"menu":"현미밥, 닭가슴살 불고기, 시금치나물, 김치","kcal":700,"nutrients":{{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}}}},
  "dinner":    {{"menu":"잡곡밥, 연어구이, 구운채소, 미역국","kcal":600,"nutrients":{{"protein_g":0,"carbs_g":0,"fat_g":0,"fiber_g":0}}}},
  "total_kcal": 1800
}}
""".strip()

async def llm_complete_open(prompt: str) -> Optional[Dict[str, Any]]:
    url = f"{OLLAMA_HOST}/api/generate"
    seed = int(datetime.utcnow().timestamp())
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.8, "repeat_penalty": 1.1, "seed": seed}
    }
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
    fiber = total_nutrients.get("fiber_g", 0)
    return (
        f"목표 {goal_kcal} kcal에 맞춰 탄수 50%·단백질 25%·지방 25%로 배분하고, "
        f"끼니는 한 가지 스타일로 맞춰 조합의 이질감을 줄였어요"
        + (f" (식이섬유≈{fiber} g)." if fiber else ".")
    )

# =========================
# 6) Fallback — 랜덤 회전 메뉴(스타일 일관)
# =========================
FALLBACK_BANK = {
    "breakfast": [
        "현미밥, 달걀국, 두부조림, 김치",
        "잡곡밥, 북어국, 오징어볶음, 시금치나물",
        "통밀토스트, 스크램블에그, 요거트",
        "오트밀, 바나나, 견과",
        "연어주먹밥, 미소국, 오이무침",
        "그릭요거트, 그래놀라, 블루베리",
    ],
    "lunch": [
        "현미밥, 닭가슴살 불고기, 시금치나물, 김치",
        "잡곡밥, 제육볶음, 상추겉절이, 무국",
        "치킨샐러드, 곡물빵",
        "토마토파스타, 그린샐러드",
        "연어덮밥, 미소국, 무절임",
        "쇠고기 스테이크, 구운채소, 감자",
        "볶음밥, 계란후라이, 깍두기",
      ],
    "dinner": [
        "잡곡밥, 연어구이, 구운채소, 미역국",
        "귀리밥, 두부스테이크, 브로콜리, 된장국",
        "한우불고기, 채소샐러드, 곡물빵",
        "참치샌드위치, 토마토수프, 피클",
        "초밥, 우동, 해조무침",
        "버섯리조또, 가지구이",
    ],
}

def _pick_no_overlap(rnd: random.Random, meal_key: str, used: set) -> str:
    candidates = FALLBACK_BANK[meal_key][:]
    rnd.shuffle(candidates)
    for menu in candidates:
        items = [x.strip() for x in _SPLIT_PATTERN.split(menu) if x.strip()]
        if used.isdisjoint(items):  # 겹치는 재료 최소화
            used.update(items)
            return menu
    choice = rnd.choice(FALLBACK_BANK[meal_key])
    used.update([x.strip() for x in _SPLIT_PATTERN.split(choice) if x.strip()])
    return choice

def _fallback_menu(goal_kcal: int) -> Dict[str, Any]:
    cal = _split_calories(goal_kcal)
    rnd = random.Random(int(datetime.utcnow().timestamp()))
    used = set()
    b_menu = _cohere_or_replace("breakfast", _pick_no_overlap(rnd, "breakfast", used), rnd)
    l_menu = _cohere_or_replace("lunch",     _pick_no_overlap(rnd, "lunch",     used), rnd)
    d_menu = _cohere_or_replace("dinner",    _pick_no_overlap(rnd, "dinner",    used), rnd)

    b_k, l_k, d_k = cal["breakfast"], cal["lunch"], cal["dinner"]
    b = {"menu": b_menu, "kcal": b_k, "nutrients": _compute_nutrients(b_k)}
    l = {"menu": l_menu, "kcal": l_k, "nutrients": _compute_nutrients(l_k)}
    d = {"menu": d_menu, "kcal": d_k, "nutrients": _compute_nutrients(d_k)}
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
    b["nutrients"] = _compute_nutrients(int(b["kcal"]))
    l["nutrients"] = _compute_nutrients(int(l["kcal"]))
    d["nutrients"] = _compute_nutrients(int(d["kcal"]))

def _ensure_shape_and_fit(js: Dict[str, Any], goal_kcal: int) -> Dict[str, Any]:
    def norm_meal(key: str) -> Dict[str, Any]:
        m = js.get(key, {}) or {}
        kcal = int(m.get("kcal", 0))
        menu = _normalize_menu_value(m.get("menu", ""), key)
        nutrients = m.get("nutrients")
        if not isinstance(nutrients, dict) or kcal <= 0:
            nutrients = _compute_nutrients(max(kcal, 1))
        else:
            comp = _compute_nutrients(kcal)
            nutrients = {k: int(round(nutrients.get(k, comp[k]))) for k in comp.keys()}
        return {"menu": menu, "kcal": int(kcal), "nutrients": nutrients}

    b, l, d = norm_meal("breakfast"), norm_meal("lunch"), norm_meal("dinner")

    # NEW: 끼니 조합 교정
    rnd = random.Random(int(datetime.utcnow().timestamp()))
    b["menu"] = _cohere_or_replace("breakfast", b["menu"], rnd)
    l["menu"] = _cohere_or_replace("lunch",     l["menu"], rnd)
    d["menu"] = _cohere_or_replace("dinner",    d["menu"], rnd)

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
