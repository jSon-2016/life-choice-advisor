"""JWT 签发与解析。"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.config import JWT_ACCESS_EXPIRATION_SECONDS, JWT_SECRET
from app.service.user_service import User

CLAIM_TOKEN_TYPE = "typ"
TOKEN_TYPE_ACCESS = "access"


@dataclass
class TokenIssueResult:
    token: str
    jti: str
    expires_in_seconds: int


class JwtService:
    def __init__(self) -> None:
        self._secret = JWT_SECRET
        self._expiration_seconds = JWT_ACCESS_EXPIRATION_SECONDS

    def generate_access_token(self, user: User) -> TokenIssueResult:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=self._expiration_seconds)
        jti = str(uuid4())
        payload = {
            "jti": jti,
            "sub": user.user_id,
            "roles": f"ROLE_{user.role}",
            CLAIM_TOKEN_TYPE: TOKEN_TYPE_ACCESS,
            "iat": now,
            "exp": exp,
        }
        token = jwt.encode(payload, self._secret, algorithm="HS256")
        return TokenIssueResult(token=token, jti=jti, expires_in_seconds=self._expiration_seconds)

    def parse_claims(self, token: str) -> dict:
        return jwt.decode(token, self._secret, algorithms=["HS256"])

    def extract_user_id(self, token: str) -> str:
        return str(self.parse_claims(token)["sub"])

    def extract_jti(self, token: str) -> str:
        return str(self.parse_claims(token)["jti"])

    def remaining_ttl_seconds(self, token: str) -> int:
        claims = self.parse_claims(token)
        exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        return max(int((exp - datetime.now(timezone.utc)).total_seconds()), 0)

    def is_access_token(self, token: str) -> bool:
        try:
            return self.parse_claims(token).get(CLAIM_TOKEN_TYPE) == TOKEN_TYPE_ACCESS
        except jwt.PyJWTError:
            return False

    def is_token_valid(self, token: str, user: User) -> bool:
        if not self.is_access_token(token):
            return False
        try:
            return str(self.parse_claims(token)["sub"]) == user.user_id
        except jwt.PyJWTError:
            return False
