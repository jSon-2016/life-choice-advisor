"""高考志愿 API（JWT + 存报告）。"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.controller.advisory_runner import run_advisory_with_cancel
from app.deps import advisory_service
from app.dto.gaokao import GaokaoProfile, GaokaoRecommendation
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/gaokao", tags=["高考志愿"])


@router.post("/advise", response_model=GaokaoRecommendation, summary="Multi-Agent 高考志愿建议")
async def advise_gaokao(
    profile: GaokaoProfile,          # FastAPI 自动从 JSON body 反序列化 + Pydantic 校验
    request: Request,                # 用于检测客户端断开（停止分析）
    current_user: User = Depends(get_current_user),  # JWT 鉴权，类似 @AuthenticationPrincipal
) -> GaokaoRecommendation:
    """
    Supervisor 模式：并行专家 → 辩论 → 总协调；RAG 注入院校/专业知识；结果存 MySQL。
    客户端断开或点击取消时，停止后续 Agent 调用且不保存报告。
    """
    try:
        return await run_advisory_with_cancel(
            request,
            advisory_service.advise_gaokao,
            current_user.user_id,
            profile,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"志愿分析失败: {exc}") from exc
