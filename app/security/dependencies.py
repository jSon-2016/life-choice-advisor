"""FastAPI 依赖：JWT 解析与当前用户。"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import JWT_ACCESS_BLACKLIST_ENABLED
from app.security.jwt_service import JwtService
from app.security.token_blacklist import AccessTokenBlacklist
from app.service.user_service import User, UserService

bearer_scheme = HTTPBearer(auto_error=False)

jwt_service = JwtService()
user_service = UserService()
token_blacklist = AccessTokenBlacklist()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先 POST /api/auth/login 获取 JWT",
        )
    token = credentials.credentials.strip()
    try:
        if JWT_ACCESS_BLACKLIST_ENABLED:
            jti = jwt_service.extract_jti(token)
            if token_blacklist.is_blacklisted(jti):
                raise HTTPException(status_code=401, detail="Token 已失效，请重新登录")
        user_id = jwt_service.extract_user_id(token)
        user = user_service.find_by_user_id(user_id)
        if user is None or not jwt_service.is_token_valid(token, user):
            raise HTTPException(status_code=401, detail="无效或过期的 JWT")
        return user
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="无效或过期的 JWT") from exc
