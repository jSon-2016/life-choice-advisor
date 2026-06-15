"""高考志愿 API（JWT + 存报告）。"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.controller.advisory_runner import run_advisory_with_cancel
from app.controller.sse_runner import stream_advisory_with_cancel
from app.deps import advisory_service
from app.dto.report_import import GaokaoAdviseRequest
from app.dto.gaokao import GaokaoRecommendation
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/gaokao", tags=["高考志愿"])


@router.post("/advise", response_model=GaokaoRecommendation, summary="Multi-Agent 高考志愿建议")
async def advise_gaokao(
    body: GaokaoAdviseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> GaokaoRecommendation:
    try:
        return await run_advisory_with_cancel(
            request,
            advisory_service.advise_gaokao,
            current_user.user_id,
            body.profile,
            imported_report_context=body.imported_report_context,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"志愿分析失败: {exc}") from exc


@router.post("/advise/stream", summary="SSE 流式高考志愿分析（实时进度）")
async def advise_gaokao_stream(
    body: GaokaoAdviseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return await stream_advisory_with_cancel(
        request,
        advisory_service.advise_gaokao,
        current_user.user_id,
        body.profile,
        imported_report_context=body.imported_report_context,
    )
