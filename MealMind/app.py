# app.py
<<<<<<< HEAD
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
=======
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator

logger = logging.getLogger("mealmind")
logging.basicConfig(level=logging.INFO)

# -------------------
# 환경설정
# -------------------
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120"))

def _ep(path: str) -> str:
    return f"{OLLAMA_BASE}{path}"

# -------------------
# 데이터 모델
# -------------------
class RecommendPayload(BaseModel):
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str
    yesterday_meals: Optional[str] = None

    @validator("gender")
    def v_gender(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"male", "female"}:
            raise ValueError("gender must be 'male' or 'female'")
        return v

    @validator("activity_level")
    def v_activity(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"sedentary", "light", "moderate", "active", "very_active"}:
            raise ValueError("activity_level must be one of "
                             "sedentary|light|moderate|active|very_active")
        return v


class MealBlock(BaseModel):
    title: str
    items: List[Dict[str, Any]]  # [{name, amount}]
    # 프론트 호환용 메뉴 문자열
    menu: Optional[str] = None

    # 영양값(기본 키)
    kcal: float
    carbs_g: float
    protein_g: float
    fat_g: float
    fiber_g: float
    sodium_mg: float

    # 혹시 프론트가 다른 키를 읽어도 보이게 별칭 키도 함께 제공
    calories: Optional[float] = None
    carbs: Optional[float] = None
    protein: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sodium: Optional[float] = None


class RecommendResult(BaseModel):
    breakfast: MealBlock
    lunch: MealBlock
    dinner: MealBlock
    total_kcal: float
    target_kcal: float
    reason: str
    # 프론트 호환용 별칭 (동일 값)
    goal_kcal: Optional[float] = None


# -------------------
# 유틸
# -------------------
def mifflin_st_jeor(p: RecommendPayload) -> float:
    """일일 목표칼로리(유지)를 추정"""
    if p.gender == "male":
        bmr = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age + 5
    else:
        bmr = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age - 161

    mult = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }[p.activity_level]

    return round(bmr * mult, 1)


def _ensure_tolerance(total: float, target: float, tol: float = 200.0) -> bool:
    return (target - tol) <= total <= (target + tol)


def _safe_meal(title: str) -> MealBlock:
    return MealBlock(
        title=title,
        items=[],
        menu="",
        kcal=0.0,
        carbs_g=0.0,
        protein_g=0.0,
        fat_g=0.0,
        fiber_g=0.0,
        sodium_mg=0.0,
        calories=0.0,
        carbs=0.0,
        protein=0.0,
        fat=0.0,
        fiber=0.0,
        sodium=0.0,
    )


def _items_to_menu(items: List[Dict[str, Any]]) -> str:
    if not items:
        return ""
    parts = []
    for i in items:
        if not i:
            continue
        name = str(i.get("name", "")).strip()
        amt = str(i.get("amount", "")).strip()
        parts.append(f"{name}{f'({amt})' if amt else ''}")
    return ", ".join([p for p in parts if p])


def _normalize(block: Dict[str, Any], title_fallback: str) -> MealBlock:
    try:
        items = list(block.get("items") or [])
        menu_str = block.get("menu") or _items_to_menu(items)

        kcal = float(block.get("kcal") or block.get("calories") or 0)
        carbs = float(block.get("carbs_g") or block.get("carbs") or 0)
        protein = float(block.get("protein_g") or block.get("protein") or 0)
        fat = float(block.get("fat_g") or block.get("fat") or 0)
        fiber = float(block.get("fiber_g") or block.get("fiber") or 0)
        sodium = float(block.get("sodium_mg") or block.get("sodium") or 0)

        return MealBlock(
            title=str(block.get("title") or title_fallback),
            items=items,
            menu=menu_str if menu_str else None,
            kcal=kcal,
            carbs_g=carbs,
            protein_g=protein,
            fat_g=fat,
            fiber_g=fiber,
            sodium_mg=sodium,
            calories=kcal,
            carbs=carbs,
            protein=protein,
            fat=fat,
            fiber=fiber,
            sodium=sodium,
        )
    except Exception as e:
        logger.warning("normalize failed for %s: %s", title_fallback, e)
        return _safe_meal(title_fallback)


def _build_prompt(p: RecommendPayload, target_kcal: float, live: bool) -> str:
    yesterday = p.yesterday_meals or ""
    lo = int(round(target_kcal - 200))
    hi = int(round(target_kcal + 200))

    guide = f"""
당신은 한국인 대상 영양사입니다. 아래 조건을 모두 만족하는 '하루 3끼 식단'을 **한국어로** 설계하세요.
응답은 **오직 JSON 오브젝트 1개**만 허용됩니다(마크다운/설명/코드펜스 금지).

[하드 규칙]
- 하루 총열량(TOTAL_KCAL)은 **{lo}~{hi} kcal 범위를 벗어나면 절대 안 됩니다**. 범위를 벗어나면 **분량을 조정**해 반드시 맞추세요.
- 끼니 배분: 아침 30%, 점심 40%, 저녁 30% ±10% 내에서 조정.
- 각 끼니는 아래 '스타일' 중 **딱 1가지**로 구성하고, **한 끼 안에서 스타일을 섞지 마세요**.
  (a) 한식 정식: 밥+국/찌개+반찬, (b) 면식: 국수/라면/우동 등+간단 반찬,
  (c) 빵/서양식: 샌드위치/파스타/스테이크+샐러드/수프(서양식), (d) 샐러드볼,
  (e) 일본식 정식: 돈부리/초밥/가츠동+미소국+츠케모노.
- **어울리는 조합만** 사용(예: 파스타+미역국 ❌, 비빔밥+미소국 ❌, 김치찌개+현미밥+나물 ✅, 우동+김치 ✅, 가츠동+미소국 ✅).
- 메뉴명은 **한국인이 익숙한 표기**로 작성(예: 현미밥, 미역국, 제육볶음, 우동, 가츠동, 그릭요거트 등).
- 같은 메인 요리를 아침/점심/저녁에 **중복 금지**.
- 각 끼니는 **1~4개 item**으로 구성하고, item은 {{ "name": 음식명, "amount": 분량 }} 형태.
- 각 끼니마다 **영양성분 필수 기재**: "kcal", "carbs_g", "protein_g", "fat_g", "fiber_g", "sodium_mg".
- 영양 단위: kcal / g / mg. 값은 정수 또는 소수 1자리까지.
- 가능하면 가공식품을 줄이고 채소, 단백질을 균형 있게 배치.
- 총열량이 범위를 벗어나면 **분량(amount)만 미세 조정**해서 맞추고, 메뉴 타입은 유지.

[요청자 정보]
- 성별: {p.gender}
- 나이: {p.age}
- 키: {p.height_cm} cm
- 몸무게: {p.weight_kg} kg
- 활동수준: {p.activity_level}

[전날 식사 참고]
"{yesterday}"

[스타일별 예시 구성 가이드 (참고용, 그대로 복붙 금지)]
- 한식 정식: (현미밥/잡곡밥) + (미역국/된장국/김치찌개 중 1) + (구이/볶음/나물/김치 1~2)
- 면식: (잔치국수/우동/비빔국수/짬뽕/칼국수 중 1) + (김치/단무지 등 1)
- 빵/서양식: (샌드위치/파스타/오믈렛/스테이크 중 1) + (샐러드/서양식 수프 1)
- 샐러드볼: (채소+단백질: 닭가슴살/두부/연어 등) + (곡물/과일/견과류 선택)
- 일본식 정식: (돈부리/가츠동/사케동/초밥 중 1) + (미소국 1) + (츠케모노 1)

[칼로리 타겟]
- Target total = {int(round(target_kcal))} kcal, **반드시 {lo}~{hi} kcal 유지**.
- 각 끼니 목표(대략): B 30%, L 40%, D 30% (±10% 이내), 총합은 반드시 범위 내.

[JSON SHAPE 예시(형태만 참고, 메뉴/수치는 새로 생성)]
{{
  "breakfast": {{
    "title": "아침",
    "style": "한식 정식|면식|빵/서양식|샐러드볼|일본식 정식 중 하나",
    "items": [{{"name":"현미밥","amount":"120 g"}}, {{"name":"미역국","amount":"1컵"}}, {{"name":"두부조림","amount":"80 g"}}],
    "kcal": 520, "carbs_g": 75, "protein_g": 25, "fat_g": 12, "fiber_g": 7, "sodium_mg": 900
  }},
  "lunch": {{ ... 같은 구조 ... }},
  "dinner": {{ ... 같은 구조 ... }},
  "total": {{ "kcal": 1850, "carbs_g": 240, "protein_g": 120, "fat_g": 55, "fiber_g": 25, "sodium_mg": 3300 }},
  "reason": "선택 이유와 전날 식사 반영 요점(나트륨/지방 조절 등)을 1~2문장으로 요약"
}}

생성 시 유의:
- 총합(total.kcal)이 {lo}~{hi} kcal 범위를 **반드시** 만족해야 합니다. 벗어나면 각 item의 amount를 미세 조정해 맞추세요.
- 전날 나트륨/지방 과다 시 저녁에 나트륨/포화지방을 낮추고 채소를 늘리세요.
"""
    if live:
        guide += "\n라이브 모드: 전날 나트륨/지방이 높으면 저녁의 나트륨·포화지방을 확실히 줄이고 채소 비중을 높이세요."
    return guide.strip()


_JSON_START = re.compile(r"\{", re.S)
_JSON_END = re.compile(r"\}", re.S)

def _extract_json(text: str) -> str:
    """응답에서 가장 바깥 JSON 오브젝트만 추출"""
    i = text.find("{")
    j = text.rfind("}")
    if i != -1 and j != -1 and j > i:
        return text[i : j + 1]
    return text.strip()


def _call_ollama_json(prompt: str) -> Dict[str, Any]:
    """Ollama generate 호출 후 응답(JSON 텍스트)을 dict로 반환"""
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    r = requests.post(_ep("/api/generate"), json=payload, timeout=OLLAMA_TIMEOUT_SEC)
    r.raise_for_status()
    data = r.json()
    text = data.get("response", "") if isinstance(data, dict) else ""
    s = _extract_json(text)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 느슨한 보정(후행 콤마 제거 등)
        s2 = re.sub(r",\s*([}\]])", r"\1", s)
        return json.loads(s2)


def _fallback_plan(p: RecommendPayload, target: float, why: str) -> Dict[str, Any]:
    """모델 실패 시 안전한 기본안"""
    logger.warning("fallback used: %s", why)
    # 아주 단순한 기본안 (대략 3등분)
    per = round(target / 3, 1)
    def mk(title: str) -> MealBlock:
        return MealBlock(
            title=title,
            items=[
                {"name": "현미밥", "amount": "150 g"},
                {"name": "닭가슴살", "amount": "150 g"},
                {"name": "채소", "amount": "200 g"},
            ],
            menu="현미밥(150g), 닭가슴살(150g), 채소(200g)",
            kcal=per,
            carbs_g=55.0, protein_g=35.0, fat_g=10.0, fiber_g=7.0, sodium_mg=600.0,
            calories=per, carbs=55.0, protein=35.0, fat=10.0, fiber=7.0, sodium=600.0,
        )

    b = mk("아침")
    l = mk("점심")
    d = mk("저녁")
    total = round(b.kcal + l.kcal + d.kcal, 1)
    reason = f"모델 응답 문제로 기본 식단을 제안합니다. ({why})"
    return {
        "breakfast": b.model_dump(),
        "lunch": l.model_dump(),
        "dinner": d.model_dump(),
        "total_kcal": total,
        "target_kcal": target,
        "goal_kcal": target,
        "reason": reason,
    }

# -------------------
# FastAPI
# -------------------
app = FastAPI(title="MealMind")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    # Ollama 버전 체크(실패해도 앱은 살아있음)
    ok = True
    ver = None
    try:
        r = requests.get(_ep("/api/version"), timeout=5)
        if r.ok:
            ver = r.json()
        else:
            ok = False
    except Exception as e:
        logger.info("Ollama check skipped: %s", e)
    return {"status": "ok" if ok else "degraded", "ollama": ver, "model": OLLAMA_MODEL}

@app.post("/recommend")
def recommend(payload: RecommendPayload, live: bool = Query(False)):
    target = mifflin_st_jeor(payload)

    prompt = _build_prompt(payload, target_kcal=target, live=live)
    try:
        raw = _call_ollama_json(prompt)

        b = _normalize(raw.get("breakfast", {}), "아침")
        l = _normalize(raw.get("lunch", {}), "점심")
        d = _normalize(raw.get("dinner", {}), "저녁")

        total = round(b.kcal + l.kcal + d.kcal, 1)

        note = ""
        if not _ensure_tolerance(total, target):
            note = " (참고: 총칼로리가 목표 대비 ±200kcal 범위를 벗어났을 수 있습니다.)"

        reason = str(raw.get("reason") or "").strip()
        if not reason:
            reason = "사용자 정보와 전날 식사를 반영해 균형 잡힌 식단을 구성했습니다."
        reason = (reason + note).strip()

        result = RecommendResult(
            breakfast=b, lunch=l, dinner=d,
            total_kcal=total, target_kcal=target, goal_kcal=target, reason=reason
        )
        # Pydantic 객체를 dict로 변환하여 반환
        return result.model_dump()

    except requests.Timeout:
        raise HTTPException(502, "Ollama 응답 지연(Timeout)")
    except requests.ConnectionError as e:
        raise HTTPException(502, f"Ollama 연결 실패: {e}")
    except Exception as e:
        logger.exception("추천 생성 중 오류")
        # 예외 시에도 프론트가 렌더할 수 있게 fallback 반환
        return _fallback_plan(payload, target, str(e))


if __name__ == "__main__":
    import uvicorn
    logger.info("시작")
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
>>>>>>> 7a8803c92233c9288f9926fb62cbd9aa45b9ec3e
