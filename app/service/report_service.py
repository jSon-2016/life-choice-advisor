"""报告业务逻辑。"""

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.db.models import AdvisoryReportModel
from app.dto.career import CareerProfile, CareerRecommendation
from app.dto.gaokao import GaokaoProfile, GaokaoRecommendation
from app.dto.report import ReportDetail, ReportSummary
from app.repository.report_repository import ReportRepository


class ReportService:
    def __init__(self, repository: ReportRepository) -> None:
        self._repository = repository

    def save_gaokao(
        self,
        user_id: str,
        profile: GaokaoProfile,
        result: GaokaoRecommendation,
    ) -> str:
        report_id = str(uuid4())
        title = f"{profile.province} {profile.total_score}分 志愿建议"
        row = AdvisoryReportModel(
            report_id=report_id,
            user_id=user_id,
            report_type="gaokao",
            title=title,
            summary=result.summary[:512] if result.summary else None,
            input_json=json.dumps(profile.model_dump(), ensure_ascii=False),
            result_json=json.dumps(result.model_dump(), ensure_ascii=False),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._repository.save(row)
        return report_id

    def save_career(
        self,
        user_id: str,
        profile: CareerProfile,
        result: CareerRecommendation,
    ) -> str:
        report_id = str(uuid4())
        title = f"{profile.major} @ {profile.university} 职业建议"
        row = AdvisoryReportModel(
            report_id=report_id,
            user_id=user_id,
            report_type="career",
            title=title,
            summary=result.summary[:512] if result.summary else None,
            input_json=json.dumps(profile.model_dump(), ensure_ascii=False),
            result_json=json.dumps(result.model_dump(), ensure_ascii=False),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._repository.save(row)
        return report_id

    def list_reports(self, user_id: str) -> list[ReportSummary]:
        rows = self._repository.find_by_user_order_by_created_desc(user_id)
        return [
            ReportSummary(
                reportId=r.report_id,
                reportType=r.report_type,
                title=r.title,
                summary=r.summary,
                createdAt=r.created_at,
            )
            for r in rows
        ]

    def get_report(self, user_id: str, report_id: str) -> ReportDetail | None:
        row = self._repository.find_by_id_and_user(report_id, user_id)
        if row is None:
            return None
        return ReportDetail(
            reportId=row.report_id,
            reportType=row.report_type,
            title=row.title,
            summary=row.summary,
            createdAt=row.created_at,
            inputJson=json.loads(row.input_json),
            resultJson=json.loads(row.result_json),
        )

    def require_owned(self, user_id: str, report_id: str) -> ReportDetail:
        report = self.get_report(user_id, report_id)
        if report is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="报告不存在或无权访问")
        return report
