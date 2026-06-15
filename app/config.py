"""应用配置。"""

import os

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "please-change-this-jwt-secret-key-at-least-32-chars",
)
JWT_ACCESS_EXPIRATION_SECONDS = int(os.getenv("JWT_ACCESS_EXPIRATION_SECONDS", "900"))
JWT_ACCESS_BLACKLIST_ENABLED = os.getenv("JWT_ACCESS_BLACKLIST_ENABLED", "true").lower() == "true"

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "test1")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4",
)

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "data/knowledge")
RAG_VECTOR_TOP_K = int(os.getenv("RAG_VECTOR_TOP_K", "3"))
RAG_CHROMA_PATH = os.getenv("RAG_CHROMA_PATH", "data/chroma")
RAG_RECALL_TOP_K = int(os.getenv("RAG_RECALL_TOP_K", "10"))
RAG_RERANK_TOP_N = int(os.getenv("RAG_RERANK_TOP_N", "5"))
RAG_RERANK_THRESHOLD = float(os.getenv("RAG_RERANK_THRESHOLD", "0.35"))
RAG_RRF_K = int(os.getenv("RAG_RRF_K", "60"))
RAG_RERANK_MODEL = os.getenv("RAG_RERANK_MODEL", "gte-rerank")

REPORT_CHUNK_SIZE = int(os.getenv("REPORT_CHUNK_SIZE", "1200"))
REPORT_CHUNK_OVERLAP = int(os.getenv("REPORT_CHUNK_OVERLAP", "250"))
REPORT_MAX_UPLOAD_MB = int(os.getenv("REPORT_MAX_UPLOAD_MB", "15"))
