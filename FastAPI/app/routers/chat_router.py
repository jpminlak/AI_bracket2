import os
from fastapi import APIRouter, HTTPException
from app.schema.chat_schema import ChatRequest, ChatResponse, ErrorResponse
from app.services.ollama_service import is_alive, generate_with_ollama

router = APIRouter()

USE_OLLAMA = os.getenv("USE_OLLAMA", "0")  # "1"이면 실제 모델 호출
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

@router.post("/complete", response_model=ChatResponse, responses={500: {"model": ErrorResponse}})
async def complete(req: ChatRequest):
    """
    LLM에 프롬프트를 던져 답변을 받는다. 
    USE_OLLAMA=1 이고 Ollama가 살아있으면 실제 호출, 아니면 MOCK.
    """
    if USE_OLLAMA == "1" and await is_alive():
        try:
            text, latency = await generate_with_ollama(
                prompt=req.prompt, system=req.system, model=OLLAMA_MODEL, stream=req.stream
            )
            return ChatResponse(model=OLLAMA_MODEL, content=text, latency_ms=latency)
        except Exception as e:
            # 모델 실패 시 안전하게 MOCK로 폴백
            mock = f"[MODEL FALLBACK] TypeError(또는 호출 실패). prompt='{req.prompt[:40]}...'"
            return ChatResponse(model="mock", content=mock, latency_ms=0)
    else:
        # MOCK
        mock = f"[MOCK] 모델 비활성 상태. prompt='{req.prompt[:40]}...'"
        return ChatResponse(model="mock", content=mock, latency_ms=0)

@router.get("/models")
async def models():
    """
    현재 설정된 모델 / 사용 여부 확인용
    """
    alive = await is_alive()
    return {
        "use_ollama": USE_OLLAMA == "1",
        "ollama_alive": alive,
        "model": OLLAMA_MODEL,
    }
