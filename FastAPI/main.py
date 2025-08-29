from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat_router

app = FastAPI(title="MealMind API", version="1.0.0")

# CORS (필요 시 도메인 추가)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터
app.include_router(chat_router.router, prefix="/chat", tags=["chat"])

@app.get("/ping")
def ping():
    return {"ok": True, "service": "MealMind API"}
