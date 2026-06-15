"""职业选择 API（JWT + 存报告）。"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.controller.advisory_runner import run_advisory_with_cancel
from app.controller.sse_runner import stream_advisory_with_cancel
from app.deps import advisory_service
from app.dto.report_import import CareerAdviseRequest
from app.dto.career import CareerRecommendation
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/career", tags=["职业选择"])


@router.post("/advise", response_model=CareerRecommendation, summary="Multi-Agent 职业选择建议")
async def advise_career(
    body: CareerAdviseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> CareerRecommendation:
    try:
        return await run_advisory_with_cancel(
            request,
            advisory_service.advise_career,
            current_user.user_id,
            body.profile,
            imported_report_context=body.imported_report_context,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"职业分析失败: {exc}") from exc


@router.post("/advise/stream", summary="SSE 流式职业选择分析（实时进度）")
async def advise_career_stream(
    body: CareerAdviseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return await stream_advisory_with_cancel(
        request,
        advisory_service.advise_career,
        current_user.user_id,
        body.profile,
        imported_report_context=body.imported_report_context,
    )
