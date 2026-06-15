"""Life Choice Advisor — 应用入口。

路由结构：
  /api/auth/*     登录 / 登出
  /api/gaokao/*   高考志愿
  /api/career/*   职业选择
  /api/reports/*  历史报告
  / /gaokao /career /history  静态问卷页面
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.controller.auth_controller import router as auth_router
from app.controller.career_controller import router as career_router
from app.controller.gaokao_controller import router as gaokao_router
from app.controller.report_controller import router as report_router
from app.controller.report_import_controller import router as report_import_router
from app.db.session import engine
from app.db.models import Base
from app.deps import knowledge_loader, rag_service
from app.observability.tracing import setup_logging

setup_logging()

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

app = FastAPI(
    title="Life Choice Advisor",
    description="Multi-Agent 协作：高考志愿 + 职业选择（Supervisor + RAG + JWT + MySQL）",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(gaokao_router)
app.include_router(career_router)
app.include_router(report_router)
app.include_router(report_import_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def init_db() -> None:
    """首次启动自动建表（t_advisory_report）。"""
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "knowledge_entries": len(knowledge_loader.get_entries()),
        "vector_store": rag_service._vector_store.available,
        "dashscope_configured": bool(os.getenv("DASHSCOPE_API_KEY")),
    }


@app.get("/")
def index_page():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/gaokao")
def gaokao_page():
    return FileResponse(STATIC_DIR / "gaokao.html")


@app.get("/career")
def career_page():
    return FileResponse(STATIC_DIR / "career.html")


@app.get("/history")
def history_page():
    return FileResponse(STATIC_DIR / "history.html")
