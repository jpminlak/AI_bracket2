from typing import Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    model: str
    content: str
    latency_ms: int

class ErrorResponse(BaseModel):
    message: str
