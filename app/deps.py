"""共享服务实例。"""

from app.db.session import SessionLocal
from app.repository.report_repository import ReportRepository
from app.security.dependencies import jwt_service, token_blacklist, user_service
from app.service.advisory_service import AdvisoryService
from app.service.auth_service import AuthService
from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.service.rag_service import RAGService
from app.service.report_service import ReportService

knowledge_loader = KnowledgeBaseLoader()
rag_service = RAGService(knowledge_loader)
report_repository = ReportRepository(SessionLocal)
report_service = ReportService(report_repository)
advisory_service = AdvisoryService(rag_service, report_service)
auth_service = AuthService(user_service, jwt_service, token_blacklist)
