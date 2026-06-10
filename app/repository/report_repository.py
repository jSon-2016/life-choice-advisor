"""报告数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AdvisoryReportModel


class ReportRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, report: AdvisoryReportModel) -> AdvisoryReportModel:
        with self._session_factory() as session:
            session.add(report)
            session.commit()
            session.refresh(report)
            return report

    def find_by_id_and_user(self, report_id: str, user_id: str) -> AdvisoryReportModel | None:
        with self._session_factory() as session:
            stmt = select(AdvisoryReportModel).where(
                AdvisoryReportModel.report_id == report_id,
                AdvisoryReportModel.user_id == user_id,
            )
            return session.scalars(stmt).first()

    def find_by_user_order_by_created_desc(self, user_id: str) -> list[AdvisoryReportModel]:
        with self._session_factory() as session:
            stmt = (
                select(AdvisoryReportModel)
                .where(AdvisoryReportModel.user_id == user_id)
                .order_by(AdvisoryReportModel.created_at.desc())
            )
            return list(session.scalars(stmt).all())
