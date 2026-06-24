"""개발 서버 진입점 — Celery/Redis 없이 바로 실행."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dev_routes import router

app = FastAPI(title="번역 에이전트 (개발 모드)", version="0.1.0-dev")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok", "mode": "dev"}

if __name__ == "__main__":
    uvicorn.run("dev_main:app", host="0.0.0.0", port=8000, reload=True)
