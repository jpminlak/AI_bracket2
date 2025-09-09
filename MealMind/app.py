# app.py
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
