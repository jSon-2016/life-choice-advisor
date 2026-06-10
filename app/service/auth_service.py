"""登录与登出。"""

from app.config import JWT_ACCESS_BLACKLIST_ENABLED
from app.security.jwt_service import JwtService
from app.security.token_blacklist import AccessTokenBlacklist
from app.service.user_service import User, UserService


class AuthService:
    BEARER_PREFIX = "Bearer "

    def __init__(
        self,
        user_service: UserService,
        jwt_service: JwtService,
        token_blacklist: AccessTokenBlacklist,
    ) -> None:
        self._user_service = user_service
        self._jwt_service = jwt_service
        self._token_blacklist = token_blacklist

    def login(self, user_id: str, password: str) -> tuple[User, str, int]:
        user = self._user_service.authenticate(user_id.strip(), password)
        if user is None:
            raise ValueError("userId 或 password 错误")
        issued = self._jwt_service.generate_access_token(user)
        return user, issued.token, issued.expires_in_seconds

    def logout(self, authorization_header: str | None) -> None:
        if not JWT_ACCESS_BLACKLIST_ENABLED:
            return
        token = self._resolve_bearer_token(authorization_header)
        if not token or not self._jwt_service.is_access_token(token):
            return
        try:
            jti = self._jwt_service.extract_jti(token)
            ttl = self._jwt_service.remaining_ttl_seconds(token)
            self._token_blacklist.blacklist(jti, ttl)
        except Exception:
            return

    def _resolve_bearer_token(self, authorization_header: str | None) -> str | None:
        if not authorization_header or not authorization_header.startswith(self.BEARER_PREFIX):
            return None
        return authorization_header[len(self.BEARER_PREFIX) :].strip() or None
