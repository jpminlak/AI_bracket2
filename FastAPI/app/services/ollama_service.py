import os
import time
import httpx
from typing import Optional

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

async def is_alive() -> bool:
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except Exception:
        return False

async def generate_with_ollama(prompt: str, system: Optional[str], model: str, stream: bool) -> str:
    """
    Ollama /api/generate 호출 (stream=False 기본).
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt if system is None else f"System: {system}\n\nUser: {prompt}",
        "stream": stream,
    }

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)
    r.raise_for_status()
    data = r.json()

    # /api/generate 는 stream=false일 때 전체 결과가 "response" 필드로 옴
    content = data.get("response", "")
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return content, latency_ms
