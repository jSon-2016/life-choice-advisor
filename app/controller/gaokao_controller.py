"""高考志愿 API（JWT + 存报告）。"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps import advisory_service
from app.dto.gaokao import GaokaoProfile, GaokaoRecommendation
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/gaokao", tags=["高考志愿"])


@router.post("/advise", response_model=GaokaoRecommendation, summary="Multi-Agent 高考志愿建议")
def advise_gaokao(
    profile: GaokaoProfile,
    current_user: User = Depends(get_current_user),
) -> GaokaoRecommendation:
    """
    Supervisor 模式：并行专家 → 辩论 → 总协调；RAG 注入院校/专业知识；结果存 MySQL。
    """
    try:
        return advisory_service.advise_gaokao(current_user.user_id, profile)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"志愿分析失败: {exc}") from exc
