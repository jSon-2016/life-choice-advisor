"""认证 API。"""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.deps import auth_service
from app.dto.auth import LoginRequest, MessageResponse, TokenResponse
from app.security.dependencies import get_current_user
from app.service.user_service import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    if not request.user_id.strip() or not request.password:
        raise HTTPException(status_code=400, detail="userId 与 password 不能为空")
    try:
        user, token, expires = auth_service.login(request.user_id, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse.of(token, user.user_id, user.role, expires)


@router.get("/me", response_model=TokenResponse)
def me(current_user: User = Depends(get_current_user)) -> TokenResponse:
    return TokenResponse.profile(current_user.user_id, current_user.role)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, current_user: User = Depends(get_current_user)) -> MessageResponse:
    auth_service.logout(request.headers.get("Authorization"))
    return MessageResponse(message="已登出")
