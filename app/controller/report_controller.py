"""历史报告 API。"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps import report_service
from app.dto.report import ReportDetail, ReportSummary
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
def list_reports(current_user: User = Depends(get_current_user)) -> list[ReportSummary]:
    return report_service.list_reports(current_user.user_id)


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(report_id: str, current_user: User = Depends(get_current_user)) -> ReportDetail:
    report = report_service.get_report(current_user.user_id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report
