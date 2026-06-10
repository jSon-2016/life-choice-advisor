"""职业选择 API（JWT + 存报告）。"""

from fastapi import APIRouter, Depends, HTTPException

from app.deps import advisory_service
from app.dto.career import CareerProfile, CareerRecommendation
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/career", tags=["职业选择"])


@router.post("/advise", response_model=CareerRecommendation, summary="Multi-Agent 职业选择建议")
def advise_career(
    profile: CareerProfile,
    current_user: User = Depends(get_current_user),
) -> CareerRecommendation:
    """
    Supervisor 模式：并行专家 → 辩论 → 总协调；RAG 注入行业知识；结果存 MySQL。
    """
    try:
        return advisory_service.advise_career(current_user.user_id, profile)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"职业分析失败: {exc}") from exc
