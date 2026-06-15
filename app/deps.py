"""共享服务实例（模块级单例，类似 Spring @Bean）。

依赖链：KnowledgeBaseLoader → RAGService → AdvisoryService → ReportService
"""

from app.db.session import SessionLocal
from app.repository.report_repository import ReportRepository
from app.security.dependencies import jwt_service, token_blacklist, user_service
from app.service.advisory_service import AdvisoryService
from app.service.auth_service import AuthService
from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.service.rag_service import RAGService
from app.service.report_import_service import ReportImportService
from app.service.report_service import ReportService
from app.tools.registry import init_knowledge_tools

knowledge_loader = KnowledgeBaseLoader()       # 加载 data/knowledge/*.txt
init_knowledge_tools(knowledge_loader)         # 初始化 Tool Calling 知识库
rag_service = RAGService(knowledge_loader)     # Hybrid RAG 检索
report_import_service = ReportImportService()
report_repository = ReportRepository(SessionLocal)
report_service = ReportService(report_repository)
advisory_service = AdvisoryService(rag_service, report_service)  # 核心咨询编排
auth_service = AuthService(user_service, jwt_service, token_blacklist)
